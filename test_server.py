import json
import threading
import unittest
from urllib.request import urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from server import Gateway, MockERP, web_handler, catalogue_xml, decode_inventory, parse_xml
class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.erp=ThreadingHTTPServer(('127.0.0.1',0),MockERP)
        cls.web=ThreadingHTTPServer(('127.0.0.1',0),web_handler(Gateway('http://127.0.0.1:%s/soap'%cls.erp.server_port)))
        for service in (cls.erp,cls.web):
            threading.Thread(target=service.serve_forever,daemon=True).start()
        cls.base='http://127.0.0.1:%s'%cls.web.server_port
    @classmethod
    def tearDownClass(cls):
        for service in (cls.erp,cls.web):
            service.shutdown();service.server_close()
    def test_live_rest_to_soap(self):
        with urlopen(self.base+'/api/inventory') as r: data=json.load(r)
        self.assertEqual(data['products'][0]['priceFils'],32500)
        self.assertEqual(data['products'][2]['stock'],0)
        self.assertEqual(data['attempts'],1)
        self.assertTrue(data['requestId'])
    def test_outage_and_recovery(self):
        with self.assertRaises(HTTPError) as failure: urlopen(self.base+'/api/inventory?scenario=outage')
        self.assertEqual(failure.exception.code,503)
        with urlopen(self.base+'/api/inventory') as r: self.assertEqual(r.status,200)
    def test_dtd_rejected(self):
        with self.assertRaises(ValueError): parse_xml(b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>')
    def test_large_xml_rejected(self):
        with self.assertRaises(ValueError): parse_xml(b'x'*32769)
    def test_contract_validated(self):
        with self.assertRaises(ValueError): decode_inventory(b'<inventory/>')
    def test_negative_stock_rejected(self):
        with self.assertRaises(ValueError): decode_inventory(catalogue_xml().replace(b'>24<',b'>-1<'))
    def test_unknown_route(self):
        with self.assertRaises(HTTPError) as failure: urlopen(self.base+'/../../server.py')
        self.assertEqual(failure.exception.code,404)
if __name__=='__main__': unittest.main()
