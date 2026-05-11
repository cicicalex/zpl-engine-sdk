# Motor propriu **C / C++** — `libcurl` / TLS pe **proces server**

Dacă ai un **runtime custom** (fără Unity/Unreal), modelul ZPL rămâne: **un singur proces** (sau container) care deține cheia face **HTTPS** către ZPL sau către **BFF**; clienții primesc doar **rezultate agregate** prin protocolul tău de joc.

## Implementare tipică

- **libcurl** (sau **mbedTLS** + stack HTTP propriu) într-un **daemon** / **worker** care rulează lângă simulare.
- **Thread pool / event loop:** nu bloca bucla principală de tick fără coadă; tratează `401/402/429` ca în [INTEGRATIONS_UNITY_GODOT_UNREAL.md](../INTEGRATIONS_UNITY_GODOT_UNREAL.md#http-comun-unity-godot-unreal).

## Alternative

- **Microserviciu** Node/Python cu SDK oficial — motorul tău C trimite observații prin **gRPC / TCP / pipe** local (vezi [SDK_VS_HTTP.md](../SDK_VS_HTTP.md)).

OpenAPI: [openapi.yaml](../../openapi.yaml).
