"""MaterialFlow ERP integration lab. Python 3.9+, standard library only."""
import json
import time
import uuid
import socket
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET

SOAP = 'http://schemas.xmlsoap.org/soap/envelope/'
ERP = 'urn:materialflow:demo'
LIMIT = 32768
PRODUCTS = [
    {'sku': 'MF-100', 'name': 'Chrome basin mixer', 'stock': 24, 'priceFils': 32500},
    {'sku': 'MF-200', 'name': 'Rain shower set', 'stock': 8, 'priceFils': 89000},
    {'sku': 'MF-300', 'name': 'Porcelain tile box', 'stock': 0, 'priceFils': 6400},
    {'sku': 'MF-400', 'name': 'Vanity cabinet', 'stock': 5, 'priceFils': 145000},
]


def parse_xml(raw):
    if len(raw) > LIMIT or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('Unsafe or oversized XML')
    # This demo accepts UTF-8 only; this also prevents alternate-encoding DTD bypasses.
    text = raw.decode('utf-8')
    if '\x00' in text:
        raise ValueError('UTF-8 XML required')
    return ET.fromstring(text)


def envelope(operation):
    root = ET.Element('{%s}Envelope' % SOAP)
    body = ET.SubElement(root, '{%s}Body' % SOAP)
    node = ET.SubElement(body, '{%s}%s' % (ERP, operation))
    return root, node


def catalogue_xml():
    root, node = envelope('GetInventoryResponse')
    for product in PRODUCTS:
        item = ET.SubElement(node, '{%s}Item' % ERP)
        for key, value in product.items():
            ET.SubElement(item, '{%s}%s' % (ERP, key)).text = str(value)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def decode_inventory(raw):
    root = parse_xml(raw)
    if root.tag != '{%s}Envelope' % SOAP:
        raise ValueError('Invalid SOAP envelope')
    response = root.find('{%s}Body/{%s}GetInventoryResponse' % (SOAP, ERP))
    if response is None:
        raise ValueError('ERP returned no inventory response')
    products, seen = [], set()
    for item in response.findall('{%s}Item' % ERP):
        p = {key: item.findtext('{%s}%s' % (ERP, key)) for key in ('sku', 'name', 'stock', 'priceFils')}
        if not p['sku'] or not p['name'] or p['sku'] in seen:
            raise ValueError('Invalid or duplicate product')
        p['stock'], p['priceFils'] = int(p['stock']), int(p['priceFils'])
        if p['stock'] < 0 or p['priceFils'] < 0:
            raise ValueError('Negative inventory value')
        seen.add(p['sku'])
        products.append(p)
    return products


class Gateway:
    def __init__(self, url):
        self.url = url

    def inventory(self, scenario='normal'):
        root, _ = envelope('GetInventory')
        started = time.monotonic()
        # Retry only the read operation. Never blindly retry order/payment writes.
        for attempt in range(1, 3):
            try:
                request = Request(self.url, data=ET.tostring(root), headers={
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction': 'GetInventory', 'X-Demo-Scenario': scenario})
                with urlopen(request, timeout=2) as response:
                    payload = response.read(LIMIT + 1)
                return {'products': decode_inventory(payload), 'source': 'mock-soap-erp',
                        'currency': 'AED', 'attempts': attempt,
                        'elapsedMs': round((time.monotonic() - started) * 1000),
                        'syncedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
            except (HTTPError, URLError, TimeoutError, socket.timeout, ValueError, ET.ParseError, TypeError) as error:
                if attempt == 2:
                    raise RuntimeError('ERP unavailable. Retry when the service recovers.') from error
                time.sleep(0.1)


class QuietHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, status, data, content_type='application/json'):
        payload = json.dumps(data).encode() if content_type == 'application/json' else data
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(payload)


class MockERP(QuietHandler):
    def do_POST(self):
        if self.path != '/soap':
            return self.reply(404, {'error': 'Not found'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= LIMIT:
                return self.reply(413, {'error': 'Invalid request size'})
            root = parse_xml(self.rfile.read(length))
            if root.tag != '{%s}Envelope' % SOAP or root.find('{%s}Body/{%s}GetInventory' % (SOAP, ERP)) is None:
                raise ValueError('Unknown SOAP operation')
        except (ValueError, ET.ParseError, UnicodeError):
            return self.reply(400, {'error': 'Invalid SOAP request'})
        if self.headers.get('X-Demo-Scenario') == 'outage':
            return self.reply(503, {'error': 'Simulated ERP outage'})
        return self.reply(200, catalogue_xml(), 'text/xml; charset=utf-8')


def web_handler(gateway):
    class Web(QuietHandler):
        def do_GET(self):
            if self.path == '/':
                return self.reply(200, Path(__file__).with_name('index.html').read_bytes(), 'text/html; charset=utf-8')
            if self.path == '/api/health':
                return self.reply(200, {'status': 'ok', 'mode': 'local-personal-demo'})
            if self.path not in ('/api/inventory', '/api/inventory?scenario=outage'):
                return self.reply(404, {'error': 'Not found'})
            request_id = str(uuid.uuid4())
            try:
                result = gateway.inventory('outage' if '?' in self.path else 'normal')
                return self.reply(200, dict(result, requestId=request_id))
            except RuntimeError as error:
                return self.reply(503, {'error': str(error), 'requestId': request_id, 'source': 'mock-soap-erp'})
    return Web


def main():
    erp = ThreadingHTTPServer(('127.0.0.1', 8791), MockERP)
    threading.Thread(target=erp.serve_forever, daemon=True).start()
    web = ThreadingHTTPServer(('127.0.0.1', 8790), web_handler(Gateway('http://127.0.0.1:8791/soap')))
    print('MaterialFlow ERP lab: http://127.0.0.1:8790', flush=True)
    try:
        web.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        erp.shutdown()
        erp.server_close()
        web.server_close()


if __name__ == '__main__':
    main()
