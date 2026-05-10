# Stencyl — cereri HTTP către **BFF** (blocuri + Haxe)

**Stencyl** generează **Haxe**; modelul ZPL rămâne **BFF**: jocul apelează **doar** URL-ul backend-ului tău, fără cheie ZPL în atribute de joc sau în fișierele exportate.

## În editor (blocuri)

1. Folosește comportamentul / blocurile de tip **„Request URL”** / **HTTP** (numele depind de versiunea Stencyl) cu **POST** sau **GET** către `https://api.example.com/stencyl-zpl`.
2. La **răspuns**, parsează JSON-ul doar dacă statusul indică succes; altfel nu inventa `ain` (vezi [INTEGRATIONS_UNITY_GODOT_UNREAL.md](../INTEGRATIONS_UNITY_GODOT_UNREAL.md#http-comun-unity--godot--unreal)).

## Modul „Code” (Haxe)

- Aliniază-te la [haxe-openfl-http-snippet.md](./haxe-openfl-http-snippet.md): `haxe.Http` sau `fetch` (țintă HTML5) către același BFF.

## Capcane

- **Game attributes** marcate pentru export: nu pune acolo chei secrete; folosește token de sesiune emis de serverul tău dacă e nevoie.
- **CORS:** la export **HTML5**, același scenariu ca [web-typescript-bff-snippet.md](./web-typescript-bff-snippet.md) — BFF-ul acceptă `Origin`-ul unde găzduiești jocul.

OpenAPI: [openapi.yaml](../../openapi.yaml).
