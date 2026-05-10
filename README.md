# ZPL Engine SDK (monorepo)

Official HTTP clients and API artifacts for **[ZPL Engine](https://engine.zeropointlogic.io)** — AIN / stability analysis **runs on the server**; these packages only call the public HTTPS API.

## Packages

| Package | Path | Publish name |
|---------|------|----------------|
| TypeScript | [packages/typescript](packages/typescript) | `@zeropointlogic/sdk` on npm |
| Python | [packages/python](packages/python) | `zeropointlogic` on PyPI |

## MCP (agents) vs SDK (apps)

- **Agents (Cursor, Claude Desktop, Windsurf):** install **[zpl-engine-mcp](https://www.npmjs.com/package/zpl-engine-mcp)** — `npx zpl-engine-mcp setup` for device-flow auth and MCP config. Source code may live in a separate org monorepo (e.g. `mcp/engine-mcp`); the npm package is the supported install surface.
- **Applications (Node, browsers with care, Python workers):** use the TypeScript or Python package here. Prefer **server-side** API keys; do not ship long-lived `zpl_…` secrets in public client bundles.

## Getting an API key

The SDK is a **thin HTTP client** (like Stripe or OpenAI SDKs): you pass `apiKey` in code; it does **not** run an interactive login. Production apps load the key from a **secret manager** or `ZPL_API_KEY` (or similar) injected at deploy time — never commit keys to git.

Ways to obtain a valid `zpl_u_…` user key, in typical order:

1. **Dashboard (production)** — [zeropointlogic.io](https://zeropointlogic.io) → account → **API keys** (create key, copy to env). Same pattern as “Dashboard → API keys” for other API vendors.
2. **CLI (local dev)** — [`zpl-engine-cli`](https://www.npmjs.com/package/zpl-engine-cli): `npm install -g zpl-engine-cli` then `zpl login` → device flow in the browser → key stored under `~/.zpl/config.toml`. Export `ZPL_API_KEY` from there or point your app at that file only on your machine.
3. **MCP (AI agents)** — [`zpl-engine-mcp`](https://www.npmjs.com/package/zpl-engine-mcp): `npx zpl-engine-mcp setup` → same device-flow against the site → key in `~/.zpl/config.toml` and MCP configs patched.

All authenticated engine calls (`POST /compute`, etc.) are **rejected without a valid key** (401 / 403 / quota errors from the server). The SDK does not bypass engine auth; format checks exist in MCP/CLI for defense in depth, but **authorization is always enforced on the engine**.

## Docs

- [docs/README.md](docs/README.md) — index of all documentation in `docs/`.
- [docs/openapi.yaml](docs/openapi.yaml) — OpenAPI 3.0 (source of truth for generators and Postman).
- **Public spec (GitHub Pages):** after [Pages setup](docs/GITHUB_PAGES.md), use  
  `https://cicicalex.github.io/zpl-engine-sdk/openapi.yaml` when the GitHub **repository slug** is `zpl-engine-sdk`; otherwise replace the path segment with your repo name. Verify with `curl -fsSL …/openapi.yaml | head`.
- [docs/postman/](docs/postman/) — Postman collection + import notes.
- [docs/OPENAPI_GENERATOR.md](docs/OPENAPI_GENERATOR.md) — optional multi-language client generation.
- [docs/UNITY.md](docs/UNITY.md) — Unity: server-authoritative pattern (no engine in-player; F2 C# package separate).
- [docs/games/README.md](docs/games/README.md) — integrări jocuri (toate motoarele), catalog demo web ZPL Main (`zpl_nodeweb`), snippets și registru modele dev.
- [docs/adr/0001-engine-client-telemetry.md](docs/adr/0001-engine-client-telemetry.md) — usage_log telemetry (engine + DB: Alex only).
- [docs/adr/0002-x-zpl-client-headers.md](docs/adr/0002-x-zpl-client-headers.md) — `X-ZPL-Client` / `X-ZPL-Client-Version` registry; **implemented** in TypeScript + Python SDKs.

## CI

GitHub Actions: [.github/workflows/openapi-pages.yml](.github/workflows/openapi-pages.yml) (OpenAPI public spec on Pages).

## Changelog and security

- [CHANGELOG.md](CHANGELOG.md)
- [SECURITY.md](SECURITY.md)

## Related

- Game integration docs (Unity / Godot / Unreal, demo catalog): [docs/games/README.md](docs/games/README.md)
- Internal ZPL workspace (ecosystem plan, `AGENTS.md`): outside this repo clone — see your org’s monorepo root if applicable.
