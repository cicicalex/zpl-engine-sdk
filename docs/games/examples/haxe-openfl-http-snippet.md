# Haxe + OpenFL / Heaps — `Http` / `URLRequest` către **BFF**

Scop: **Haxe** compilează spre **JavaScript**, **C++**, **HashLink**, etc. Modelul ZPL rămâne: **clientul jocului** vorbește cu **BFF-ul tău**; cheia ZPL stă pe server.

## Țintă JavaScript (OpenFL / Lime)

Aliniază-te la [web-typescript-bff-snippet.md](./web-typescript-bff-snippet.md): din Haxe poți folosi `haxe.Http` sau `js.Browser.fetch` (macro `-lib hxnodejs` / target js) către același `/api/zpl-proxy`.

```haxe
// Exemplu conceptual (target js): POST JSON la BFF
var req = new haxe.Http("https://api.example.com/haxe-zpl");
req.addHeader("Content-Type", "application/json");
req.setPostData(haxe.Json.stringify({value: 0.5, runs: 1000, scale: 8}));
req.onStatus = function (status) if (status != 200) { /* nu inventa AIN */ };
req.onData = function (data) { /* parse JSON public */ };
req.request(true);
```

## Ținte native (C++, HL)

- Preferă **HTTPS** prin biblioteca suportată de stack-ul tău (ex. curl binding) sau **apel către proces local** care face ZPL.
- **Nu** îngropa cheia în binarul distribuit; folosește BFF sau secret injectat doar în build **server**.

## OpenFL `URLRequest` (alternativă)

- Poți folosi `openfl.net.URLRequest` + `URLLoader` cu `method = POST` și `data` JSON — aceleași reguli CORS / BFF ca mai sus.

OpenAPI: [openapi.yaml](../../openapi.yaml).
