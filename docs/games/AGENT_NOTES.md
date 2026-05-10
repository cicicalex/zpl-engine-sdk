# Note pentru agenți AI (Claude, Cursor) — ZPL Games

Scop: același **model mental** pentru toți agenții care lucrează în workspace, ca să nu se contrazică documentația cu `AGENTS.md` sau cu arhitectura reală.

## Ce este **corect**

1. **AIN / formula** = trade secret pe **server Rust**; clienții publici (MCP, CLI, SDK, demos, jocuri) sunt **thin clients**.
2. **SDK TS/Python** = biblioteci pentru **Node și Python**; **nu** înlocuiesc automat `HttpClient` în Unity — acolo e HTTP nativ sau viitor SDK C# (mandat separat). **Fiecare motor de joc** = propriul glue code; nu presupune un singur pachet care acoperă Unity+Godot+Unreal.
3. **SDK fără login integrat** = normal (Stripe/OpenAI pattern); cheia vine din dashboard / CLI / MCP setup.
4. **RNG în demo-uri web** = strat de **simulare** pentru a produce observații; **nu** este „motorul ZPL descărcat”.
5. **Paritate headere** `X-ZPL-Client` / versiune: documentată în ADR 0002; MCP/CLI/SDK fiecare în zona lui de repo.

## Greșeli frecvente de evitat

| Greșeală | Corecție |
|----------|-----------|
| „Pune formula AIN în client ca să meargă offline” | Interzis — contrazice `AGENTS.md` și modelul de business. |
| „SDK-ul Unity importă `@zeropointlogic/sdk`” | Nu e cazul azi — TS e pentru Node; Unity folosește HTTP pe server sau C# generat / viitor pachet. |
| „O singură integrare pentru toate motoarele” | Fals — același API, dar **scrieri separate** per motor (și uneori per limbaj în același motor). |
| „Un singur fișier gigant e ok pentru totdeauna” | Funcționează, dar `zpl-master` merită împărțit când există mandat de refactor. |
| „Publică cheia API în repo / în prompt” | Interzis — `SECURITY.md` + politici workspace. |

## Cine modifică ce

| Zonă | Cine |
|------|------|
| `docs/games/DEMO_CATALOG.md` | Sursa de adevăr pentru slug-uri demo web; nu inventa rute noi fără blueprint site. |
| `zpl-engine-sdk` | Agent SDK + docs (Alex approve pentru breaking). |
| `mcp/engine-mcp`, `zpl-cli` | Agent MCP/CLI — **nu** amesteca schimbări SDK în același PR fără nevoie. |
| `Proiecte/zpl-engine` (Rust core) | **Doar Alex**. |
| `zpl_nodeweb` | Agent cu **blueprint**; fără pagini noi fără plan. |
| `docs/games` (acest folder în repo SDK) | Documentație conceptuală jocuri — PR-uri mici de clarificare OK. |

## Ce poate face „Cursor SDK” vs „Claude MCP/CLI”

- **Cursor (zona SDK):** OpenAPI, README-uri integrare, `UNITY.md`, exemple HTTP, versioning npm/PyPI.
- **Claude (zona MCP/CLI):** tools, `setup`, `zpl login`, parity device flow.
- **Amândoi:** nu ating `zpl-core`; nu publică secrete.
