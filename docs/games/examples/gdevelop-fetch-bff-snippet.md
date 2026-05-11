# GDevelop 5 — cereri rețea către **BFF** (extensii / evenimente)

Scop: **GDevelop** exportă adesea **HTML5 / Web** sau runtime-uri cu acces la rețea prin **extensii** (ex. „Network”, „HTTP”). **Cheia ZPL** nu intră în variabile de scenă vizibile exportului sau în fișiere JSON de proiect partajate public.

## Pattern recomandat

1. **Extensie „Network request”** (sau echivalent) cu `POST` către `https://api.example.com/gd-zpl` și corp JSON (observații).
2. **Eveniment la răspuns:** dacă status ≠ succes sau corp invalid, nu afișa scor AIN inventat (vezi [INTEGRATIONS_UNITY_GODOT_UNREAL.md](../INTEGRATIONS_UNITY_GODOT_UNREAL.md#http-comun-unity-godot-unreal)).

## JavaScript (comportamente personalizate)

- Dacă folosești **cod JS** în GDevelop, aliniază-te la [web-typescript-bff-snippet.md](./web-typescript-bff-snippet.md): `fetch` către același origin sau BFF-ul tău, fără header ZPL în client.

## Capcane

- **Variabile globale cu secret:** apar în build; folosește doar **token de sesiune** emis de serverul tău după login.
- **Preview vs export:** verifică **CORS** și URL-uri absolute pe domeniul BFF pentru toate modurile în care publici jocul (itch.io, Poki, etc.).

OpenAPI: [openapi.yaml](../../openapi.yaml).
