# AI marketplace integration (no secrets in repo)

Use [../openapi.yaml](../openapi.yaml) as the **single schema** for GPT Actions, OpenAI Tool / Responses API tools, and any generator.

## OpenAI Custom GPT (Actions)

1. Create a Custom GPT → **Actions** → **Import from URL** when the spec is hosted at a stable HTTPS URL (recommended: **GitHub Pages** after [../GITHUB_PAGES.md](../GITHUB_PAGES.md) is enabled — e.g. `https://cicicalex.github.io/zpl-engine-sdk/openapi.yaml` when the GitHub repo slug is `zpl-engine-sdk`). Alternatives: `https://raw.githubusercontent.com/.../openapi.yaml` or **Schema** → paste `openapi.yaml`.
2. Set authentication to **API Key** or **Bearer**; the end-user supplies their own ZPL key (never embed your production key in the GPT).
3. Server URL: `https://engine.zeropointlogic.io` (already in `servers` in the OpenAPI file).

## Claude (Anthropic)

- **Desktop / Cursor:** distribute **[zpl-engine-mcp](https://www.npmjs.com/package/zpl-engine-mcp)** — users run `npx zpl-engine-mcp setup`.
- **Anthropic API “tools”:** point tool definitions at the same OpenAPI operations (or duplicate minimal JSON schema for `POST /compute` only). Keep prompts free of proprietary AIN internals.

## Files

- This folder intentionally has **markdown only**; no API keys.
