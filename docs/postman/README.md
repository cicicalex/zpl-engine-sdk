# Postman

## Option A — Import OpenAPI (recommended)

1. Postman → **Import** → **File** or **Raw text**.
2. Select [`../openapi.yaml`](../openapi.yaml).
3. Postman creates a collection; set variables:
   - `baseUrl` = `https://engine.zeropointlogic.io`
   - `apiKey` = your `zpl_…` key (use **environment** or collection variable — never commit the value).

## Option B — Use bundled collection

Import [`zpl-engine.postman_collection.json`](./zpl-engine.postman_collection.json), then set the same variables.

## Auth in requests

Set **Authorization → Bearer Token** = `{{apiKey}}`, and add header `X-API-Key: {{apiKey}}` to match official SDK behaviour (either header may be enforced depending on gateway).

## Marketplace

To publish a public workspace: Postman → share workspace → **Public documentation** / community guidelines apply. Do not embed live API keys in public docs.
