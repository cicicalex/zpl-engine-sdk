# LÖVE (Love2D) — TLS și chei: preferă **BFF**, nu ZPL direct din client

Scop: runtime-ul Love2D folosește **Lua**; HTTPS din joc depinde de **luasec** / extensii sau de platformă. Cel mai predictibil pentru ZPL: **microserviciu** (Node/Python) sau **BFF** local în dev (`127.0.0.1`), iar jocul Love apelează **doar** acel endpoint fără cheie ZPL.

## Pattern recomandat (producție)

1. **Server** (Cloud Run, VPS) expune `POST /zpl-bridge` cu autentificare joc↔server (token de sesiune, nu cheia ZPL).
2. **Love2D** face `https.request` (cu biblioteca TLS aleasă de proiect) sau `socket.http` doar către acel host.

## Schiță (doar dev / LAN — fără cheie în `.love`)

```lua
-- Exemplu conceptual: înlocuiește cu stack-ul TLS real al proiectului tău.
local http = require("socket.http")
local ltn12 = require("ltn12")
local body = '{"value":0.5,"runs":1000,"scale":8}'
local response_body = {}
local _, code = http.request{
  url = "http://127.0.0.1:8787/zpl-bridge", -- BFF local de dev
  method = "POST",
  headers = { ["content-type"] = "application/json", ["content-length"] = tostring(#body) },
  source = ltn12.source.string(body),
  sink = ltn12.sink.table(response_body),
}
-- Dacă code ~= 200, nu inventa AIN.
```

În **producție** folosește **HTTPS** real; dacă integrarea TLS în Love e prea grea, **BFF-ul** rămâne pe infrastructura ta și Love vorbește doar cu el.

## Capcane

- **Cheia în `conf.lua` sau `main.lua`:** oricine despachetează `.love` o vede.
- **Lipsă TLS:** nu trimite observații sensibile pe HTTP public.

OpenAPI: [openapi.yaml](../../openapi.yaml).
