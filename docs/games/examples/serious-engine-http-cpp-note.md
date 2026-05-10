# **Serious Engine** (Croteam) — HTTPS din **dedicated server**

**Serious Engine** (folosit în seria *Serious Sam* și alte titluri Croteam) urmează același model ca **id Tech** sau **Source 2**: logica autoritară și apelurile către servicii externe (ZPL) aparțin **procesului de server dedicat** sau unui **serviciu colocated**, nu build-ului client pe care îl descarcă jucătorii.

## Recomandări

- **`libcurl`** / WinHTTP / alt client HTTP din cod C++ compilat **doar** în target-ul **dedicated server** (sau microserviciu TCP/UDP lângă serverul de joc).
- **AngelScript** sau alte straturi script: dacă rulează și pe client, **nu** încărca acolo module care citesc `ZPL_API_KEY` — limitează modulul ZPL la context **server-only**.
- **Pachete / resurse client:** tratează-le ca fișiere **nesigure** (pot fi extrase); orice secret trebuie absent.

## Referințe în repo

- [idtech-dedicated-server-http-note.md](./idtech-dedicated-server-http-note.md) — același flux „dedicated + pachete client”.
- [cryengine-http-cpp-note.md](./cryengine-http-cpp-note.md) — C++ dedicat, fără cheie în `.pak` client.
- [custom-engine-c-http-note.md](./custom-engine-c-http-note.md) — `libcurl` și worker-e C++.

OpenAPI: [openapi.yaml](../../openapi.yaml).
