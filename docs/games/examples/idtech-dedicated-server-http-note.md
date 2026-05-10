# **id Tech** (id Software) — HTTPS din **dedicated server**

Motorul **id Tech** (ex. **id Tech 7** și versiunile anterioare folosite în titluri AAA) rulează logica de server într-un **binar dedicat** separat de clientul care încarcă pachete (ex. **`.pak`** / resurse stream-uite). Integrarea ZPL respectă același principiu ca **Source 2** sau **CryEngine**: cheia API și clientul HTTPS trăiesc **doar** pe procesul **server**, nu în artefactele livrate jucătorilor pentru client.

## Recomandări

- **libcurl** / WinHTTP / strat HTTP ales de echipă, apelat din cod compilat **doar** în target **dedicated server** (sau microserviciu lângă server).
- **Fișiere `.cfg` / `.json` server:** poți referi variabile de mediu pentru cheie; **nu** replica aceleași fișiere în pachetul client fără a exclude câmpurile secrete.

## Referințe în repo

- [source2-server-http-note.md](./source2-server-http-note.md) — același model „SRCDS / dedicat”.
- [custom-engine-c-http-note.md](./custom-engine-c-http-note.md) — `libcurl` și worker-e C++.
- Concept C++ async / packaging: [unreal-http-subsystem-sketch.md](./unreal-http-subsystem-sketch.md).

OpenAPI: [openapi.yaml](../../openapi.yaml).
