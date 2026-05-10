# ZPL Games — model conceptual și integrări

Documentație pentru Alex, agenți AI (Claude, Cursor) și developeri care integrează **ZPL Engine** în jocuri. **Publicată în acest repo** sub `docs/games/`; într-un workspace ZPL mai mare poate exista și o copie oglindă `zpl-games/` la rădăcină — păstrează-le aliniate la PR-uri. **Un API HTTP**, **mai multe motoare** — fiecare (Unity, Godot, Unreal, Bevy, Defold, …) are **propriul strat de scriere** (glue); lista se extinde pe măsură ce apar motoare noi.

## Neutralitate ca strat de decizie

În practică, ZPL se aplică mai ales ca **strat de decizie privind neutralitatea**: nu înlocuiește designerul sau RNG-ul, dar oferă un **semnal repetabil** (`ain`, `ain_status`, deviație) ca să **decizi** dacă un sistem e suficient de neutru / stabil — audit live ops, gate înainte de patch, flag QA, raport. **Tu legi politica** (alertă, dezactivare nudge, cerere revizuire). Fără observații clare în contract, nu există decizie informată. ZPL **nu** înlocuiește conformitatea legală sau regulile platformelor.

**Nu** conține formula AIN, `zpl-core` sau secrete. **Nu** înlocuiește blueprint-ul `SITE_BLUEPRINT_ZPL_MAIN.md` pentru pagini noi pe site.

## Fișiere

| Fișier | Scop |
|--------|------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Straturi: simulare joc → observații → API → motor |
| [SDK_VS_HTTP.md](./SDK_VS_HTTP.md) | Când `@zeropointlogic/sdk` / `zeropointlogic` vs `fetch`/`HTTPRequest` direct |
| [INTEGRATIONS_UNITY_GODOT_UNREAL.md](./INTEGRATIONS_UNITY_GODOT_UNREAL.md) | Matrice motoare, Unity/Godot/Unreal + HTTP comun + linkuri snippets |
| [UNITY_ENGINE_GAP.md](./UNITY_ENGINE_GAP.md) | Ce acoperă `docs/UNITY.md` vs gap-uri |
| [DEMO_CATALOG.md](./DEMO_CATALOG.md) | Catalog slug-uri demo web (`zpl_nodeweb`) + poziționare |
| [DEV_GAME_MODELS.md](./DEV_GAME_MODELS.md) | Registru șablon pentru modele în dev (completat de tine) |
| [GEN_ENGINE_CROSSWALK.md](./GEN_ENGINE_CROSSWALK.md) | Ghid gen gameplay ↔ pattern integrare (D3) |
| [TEMPLATE_REPOS_PHASE_B.md](./TEMPLATE_REPOS_PHASE_B.md) | Backlog opțional: repo-uri `zpl-integration-*` |
| [WEB_DEMOS.md](./WEB_DEMOS.md) | Legătura cu `zpl_nodeweb` `/demos` (referință cod) |
| [AGENT_NOTES.md](./AGENT_NOTES.md) | Model mental corect vs greșeli frecvente la agenți |
| [examples/](./examples/) | Snippets Godot / Unity / Unreal |

## Legături utile

- SDK monorepo: [../../README.md](../../README.md), [UNITY.md](../UNITY.md)
- OpenAPI public (după Pages): vezi [GITHUB_PAGES.md](../GITHUB_PAGES.md)
- Reguli workspace (repo ZPL mai larg): fișierul `AGENTS.md` din workspace-ul tău local; pe GitHub public poate lipsi — respectă politica proiectului.
