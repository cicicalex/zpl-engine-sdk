# GameMaker — `http_request` / async (GML), fără cheie în runner

Scop: **Windows / console / GX** — cheia ZPL stă pe **server dedicat** sau **middle tier**; clientul GameMaker apelează **doar** URL-ul tău. Dacă scrii un **headless** tool intern cu GML sau extensie server, poți folosi `http_request` către ZPL doar acolo.

## Pattern recomandat

- **Client:** `http_request("https://api.tauproject.ro/zpl-bridge", "POST", headers, body)` — fără header `Authorization` ZPL.
- **Bridge:** Node/Python cu SDK sau `fetch` către ZPL (vezi [SDK_VS_HTTP.md](../SDK_VS_HTTP.md)).

## Schiță GML (doar mediu server / tool)

```gml
/// @description POST către ZPL — NU în executabil distribuit jucătorilor
var _url = "https://engine.zeropointlogic.io/compute";
var _key = environment_get_variable("ZPL_API_KEY"); // setat pe mașina server
var _map = ds_map_create();
ds_map_add(_map, "Content-Type", "application/json");
ds_map_add(_map, "Authorization", "Bearer " + string(_key));
var _body = json_stringify({ value: 0.5, runs: 1000, scale: 8 });
var _rid = http_request(_url, "POST", _map, _body);
ds_map_destroy(_map);
// În Async - HTTP: parsează id vs _rid; verifică http_status; nu loga cheia.
```

## Capcane GameMaker

- **Export GX / HTML5:** orice string literal de cheie poate fi extras; folosește bridge.
- **`http_request` async:** gestionează coliziuni de `id` și timeout-uri (nu retry agresiv pe 401/402).
- **JSON:** `json_parse` pe răspuns; validează câmpurile așteptate înainte de UI.

OpenAPI: [openapi.yaml](../../openapi.yaml).
