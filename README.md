# MaterialFlow ERP integration lab

Personal portfolio project by Sheik Mohamed Hanifa. A runnable, mobile-friendly catalogue demonstrating REST/JSON to SOAP/XML integration with a **synthetic ERP service**. It is not Dynamics AX, a SANIPEX product, an employer project, or production experience.

## Run locally

Python 3.9 or newer; no third-party packages or credentials required.

```sh
python3 -m unittest -v
python3 server.py
```

Open http://127.0.0.1:8790. The web/REST server listens on loopback port 8790 and the independent mock SOAP service on port 8791. Stop with Ctrl-C. Do not expose this unauthenticated learning service publicly.

## Demonstrate in two minutes

1. Open the catalogue: four synthetic products, prices in AED and stock from the SOAP service.
2. Search `shower` and clear the search.
3. Expand **Inspect the API response**: explain integer fils, request ID, latency and sync time.
4. Select **Simulate ERP outage**: the mock ERP returns HTTP 503; the gateway retries once and reports a clear failure. Stale inventory is cleared.
5. Select **Sync inventory**: demonstrate recovery without reloading the page.

This is a demo walkthrough script, not a recorded video.

## Architecture

Browser HTML/CSS/JavaScript → GET /api/inventory → Python REST gateway → HTTP SOAP GetInventory → separate Python mock ERP → XML contract validation → JSON response.

- `server.py`: both independent HTTP services, XML conversion, bounded responses, timeout and read retry.
- `index.html`: responsive catalogue, filtering, progress, failure and recovery UI. DOM text insertion avoids treating product data as HTML.
- `test_server.py`: seven tests covering live HTTP integration, outage/recovery, DTD rejection, oversized XML, wrong contract, negative stock and unknown paths.
- No database: read-only synthetic inventory is reset with the process. No accounts, order placement, cloud backend or native app are implemented in this standalone lab.

## Why this fits the target role

The referenced SANIPEX Mobile Application Developer role asks for native/cross-platform development, REST/SOAP, JSON/XML, integration, debugging and release knowledge. This lab demonstrates the **integration and error-handling portion** with inspectable code. It complements, but does not replace, native iOS and cross-platform samples in the broader MaterialFlow project.

Job reference: https://www.linkedin.com/jobs/view/4474180773/

Python is an implementation choice for a dependency-free, easily runnable integration example; it is not represented as a requirement in that JD. No claim of Dynamics AX 2012 access or experience is made.

## Interview explanation

“I built an AI-assisted personal lab to understand a REST-to-SOAP boundary. The client only understands JSON; the gateway owns the ERP contract. It rejects unsafe XML and invalid inventory, bounds request time, and retries the read operation once. I can demonstrate failure and recovery. A real AX integration would require the customer's service contract, authentication and a staging environment.”

Before presenting this as your work, run the flow, read the adapter, modify a product and explain every test. Describe AI assistance candidly.

## Production gaps and next implementation steps

Add authenticated access, structured monitoring, TLS, rate limiting and a provider-specific WSDL/client. Enforce endpoint configuration through a server allowlist. Add persistent inventory snapshots with visible staleness and reconciliation. Order creation needs transactions and idempotency; never apply this read retry policy blindly to financial or stock-changing writes. Native clients should keep credentials out of source, handle lifecycle changes and show offline state.

Do not deploy this long-running two-port Python demo directly as a static Vercel site. The portfolio can be hosted there; the service needs an appropriate backend host or adaptation to supported serverless endpoints.

## Verification

2026-10-03: `python3 -m unittest -v` — 7 tests passed on macOS/Python 3.9. Browser checks are recorded separately after execution.

Browser verification: catalogue loaded four products; search `shower` showed only the rain shower; simulated outage cleared inventory and displayed recovery guidance; Sync inventory restored all four products.
