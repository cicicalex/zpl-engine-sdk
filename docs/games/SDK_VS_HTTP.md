# SDK vs HTTP direct — ce folosește un joc?

**Per motor:** integrarea se scrie **separat** (C# în Unity, GDScript/C# în Godot, C++ în Unreal, Lua în Defold, etc.). Nu există o singură „scriere” care acoperă toate motoarele — doar același **contract HTTP** și aceleași reguli (cheia pe server, nu în client).

## Răspuns scurt

| Context | Recomandare |
|---------|-------------|
| **Unity / Godot / Unreal (C# / GDScript / C++)** | De obicei **HTTP client nativ** (Unity `UnityWebRequest` / `HttpClient`, Godot `HTTPRequest`, Unreal `FHttpModule`) din **serverul de joc** care ține cheia API. **SDK TypeScript/Python** sunt pentru **Node și Python**, nu pentru runtime-ul grafic al jocului. |
| **Backend Node.js / Python** (matchmaking, live ops) | **`@zeropointlogic/sdk`** sau **`zeropointlogic`** (PyPI) — retry, tipuri, headere ADR 0002, erori normalizate. |
| **Web Next.js** (ex. `zpl_nodeweb` demos) | **`fetch`** către **`/api/compute`** BFF care aplică rate limits și nu expune cheia în browser — pattern-ul actual al demo-urilor. |

## Când are sens SDK-ul

- Echipa scrie deja în **TypeScript** sau **Python**.
- Vrei **paritate** cu OpenAPI, semver, `X-ZPL-Client`, handling erori comun.

## Când are sens doar HTTP

- **C# / C++ / Rust / Go** pe server de joc — SDK-urile oficiale actuale nu sunt aceste limbaje; folosești generator OpenAPI (vezi [OPENAPI_GENERATOR.md](../OPENAPI_GENERATOR.md)) sau un client subțire manual.
- **Browser** — nu îngropa cheia lungă în bundle; cheama **BFF-ul** tău.

## Ce **nu** face SDK-ul

- **Nu** include device flow / login (la fel ca Stripe SDK). Cheia vine din dashboard / `zpl login` / MCP setup — vezi [README.md](../../README.md) secțiunea *Getting an API key*.
