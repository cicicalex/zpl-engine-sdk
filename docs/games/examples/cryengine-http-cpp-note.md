# CryEngine / **Amazon Lumberyard** (C++) — HTTP pe **server**

În **CryEngine** și derivate (**Lumberyard** spre **O3DE**), integrarea ZPL respectă același model ca **Unreal**: **`IHttpRequest`** / client HTTP din **GameDLL** sau plugin care rulează pe **dedicated server** sau pe un **serviciu lateral**, cu cheia în **env** pe mașina server.

## Recomandări

- **Nu** expune cheia în **`.pak`** / resurse client sau în **CVars** replicate.
- **Flowcharts / Lua:** cel mult declanșează un apel C++ către propriul endpoint care face HTTPS (ca Blueprint → C++ în Unreal).

## Referință conceptuală

- [unreal-http-subsystem-sketch.md](./unreal-http-subsystem-sketch.md) — pattern-uri de threading și răspuns HTTP aplicabile conceptual; adaptează la API-ul CryEngine/LY folosit de proiect.

OpenAPI: [openapi.yaml](../../openapi.yaml).
