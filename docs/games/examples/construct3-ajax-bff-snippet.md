# Construct 3 — **AJAX** către BFF (browser / NW.js / Cordova)

Scop: în **Construct 3**, apelurile rețea se fac de obicei cu obiectul **AJAX** (sau pluginuri echivalente). **Cheia ZPL nu intră** în proiectul `.c3p` / export HTML5 — doar URL-ul **BFF-ului** tău (același contract JSON ca în [web-typescript-bff-snippet.md](./web-typescript-bff-snippet.md)).

## Flux

1. Eveniment: „On button clicked” → **AJAX: Post** la `https://api.example.com/c3-zpl` cu body JSON (observații).
2. **AJAX: On completed** → parsează răspunsul; dacă status ≠ succes, nu inventa `ain`.

## Setări Construct

- **Preview în browser:** adaugă domeniul BFF în lista permisă (Construct cere explicit domeniile pentru `AJAX` în unele moduri de export — vezi manualul pentru versiunea ta).
- **CORS:** BFF-ul trebuie să accepte `Origin`-ul jocului tău (sau același origin dacă hostezi jocul în spatele aceluiași domeniu).

## Capcane

- **Cheia în variabile globale vizibile în export:** oricine deschide DevTools vede valorile; folosește doar token de sesiune emis de serverul tău, nu ZPL.
- **Cordova / Capacitor:** la fel — apel doar la BFF; cheia ZPL rămâne pe backend.

Coduri HTTP: [INTEGRATIONS_UNITY_GODOT_UNREAL.md](../INTEGRATIONS_UNITY_GODOT_UNREAL.md#http-comun-unity--godot--unreal).

OpenAPI: [openapi.yaml](../../openapi.yaml).
