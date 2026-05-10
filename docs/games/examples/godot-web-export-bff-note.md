# Godot — export **Web (HTML5 / WASM)** și ZPL

În build-ul **browser**, nu există același „dedicated server” ca pe desktop: codul GDScript rulează în **WASM** în mașina jucătorului. **Cheia ZPL nu poate fi ascunsă** dacă o încarci în clientul descărcat de browser.

## Model recomandat

1. **Client Godot Web:** `HTTPRequest` (sau echivalent) către **BFF-ul tău** (HTTPS), același contract JSON ca în [web-typescript-bff-snippet.md](./web-typescript-bff-snippet.md).
2. **BFF** ține cheia ZPL și apelează `engine.zeropointlogic.io` (sau proxy intern).

## Multiplayer Web

- Dacă folosești **relay / host** în browser, tratează apelurile ZPL ca fiind responsabilitatea **serverului tău autoritar** (nod dedicat în cloud), nu a peer-ilor WASM care ar trebui să dețină secrete.

## Legătură cu snippet-ul server desktop

- Pentru **Windows/Linux/macOS** cu `multiplayer.is_server()`, vezi [godot-server-snippet.md](./godot-server-snippet.md). Exportul Web e **caz separat**: aproape mereu **BFF**, nu cheie în `HTTPRequest` direct către ZPL.

OpenAPI: [openapi.yaml](../../openapi.yaml).
