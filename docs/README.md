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

## Edits under `docs/games/`

Before a PR: from the **repo root** run `pwsh ./scripts/verify-docs-games.ps1` (same checks as workflow [verify-docs-games.yml](../.github/workflows/verify-docs-games.yml)). If you use a wider workspace with a mirrored `zpl-games/` tree, run your workspace `tools/sync-zpl-games-to-sdk.ps1` first so links and nested `README.md` files (e.g. under `examples/`) stay aligned — see [games/README.md](./games/README.md).

For **npm / PyPI** client usage, start at the repo root [README.md](../README.md) and the package READMEs under `packages/`.
