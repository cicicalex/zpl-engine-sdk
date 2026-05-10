# ZPL Engine SDK — documentation index

| Document | Purpose |
|----------|---------|
| [openapi.yaml](./openapi.yaml) | OpenAPI 3.0 — contract for `POST /compute` and related endpoints |
| [GITHUB_PAGES.md](./GITHUB_PAGES.md) | Publish `docs/` to GitHub Pages (OpenAPI URL) |
| [OPENAPI_GENERATOR.md](./OPENAPI_GENERATOR.md) | Optional codegen (C#, Go, etc.) from OpenAPI |
| [UNITY.md](./UNITY.md) | Unity: server-authoritative integration (F1) |
| [games/README.md](./games/README.md) | **Games:** all engines (Godot, Unreal, …), demo catalog, HTTP snippets, dev registry |
| [verify-docs-games.ps1](../scripts/verify-docs-games.ps1) | Local + CI: validate `docs/games` markdown (no sibling `zpl-engine-sdk` links, no `C:\Dev` literals); workflow `verify-docs-games.yml` |
| [postman/](./postman/) | Postman collection |
| [adr/](./adr/) | Architecture decision records |

For **npm / PyPI** client usage, start at the repo root [README.md](../README.md) and the package READMEs under `packages/`.
