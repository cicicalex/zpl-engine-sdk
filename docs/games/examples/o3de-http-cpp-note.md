# O3DE — HTTPS către ZPL sau BFF din **proces server**

**Open 3D Engine (O3DE)** este modular (**Gems**, **ScriptCanvas**, **AZ::Component**). Integrarea ZPL urmează aceeași regulă ca **Unreal**: cheia API și apelurile HTTPS către `engine.zeropointlogic.io` (sau către **BFF**) rulează din **logica de server dedicat** / **headless**, nu din pachetul clientului descărcat de jucători.

## Orientare practică

- Plasează clientul HTTP (ex. **AWS Common Runtime HTTP**, **libcurl**, sau stratul recomandat de echipa ta) într-un **Gem** sau **SystemComponent** încărcat **doar** pe target **server** / **dedicated**.
- **ScriptCanvas / Lua:** folosește-le cel mult ca orchestrator care cheamă un **serviciu C++** care face POST-ul; nu pune cheia în variabile replicate către client.
- **Multiplayer:** dacă folosești **O3DE Multiplayer Gem**, tratează ZPL ca **autoritar pe host dedicat**, similar ideii `NM_DedicatedServer` din [unreal-lyra-packaging-note.md](./unreal-lyra-packaging-note.md).

## Referință conceptuală

- Checklist C++ (async, packaging, fără cheie în client): [unreal-http-subsystem-sketch.md](./unreal-http-subsystem-sketch.md) — principii transferabile, API-ul O3DE diferă.

OpenAPI: [openapi.yaml](../../openapi.yaml).
