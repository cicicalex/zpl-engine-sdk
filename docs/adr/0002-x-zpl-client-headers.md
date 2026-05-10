# ADR 0002: `X-ZPL-Client` and `X-ZPL-Client-Version` headers

## Status

Accepted — **SDK** (TypeScript + Python) sends these headers from this commit. MCP, CLI, GPT Action, Telegram, bookmarklet, and other channels adopt the same contract in their repos. **Engine persistence** (`usage_log.client_type`, `usage_log.client_version`) remains **Alex / Rust** (see [0001](./0001-engine-client-telemetry.md)).

## Context

We need a stable, parser-friendly way to attribute traffic per product family, independent of `User-Agent` free text. `User-Agent` stays required (browser-like, semver in product token) for Cloudflare compatibility; the two headers add explicit identity for dashboards and logs once the engine stores them.

## Decision

Every HTTP client **SHOULD** send on **every** engine request:

| Header | Value |
|--------|--------|
| `X-ZPL-Client` | Lowercase **kebab-ish** slug identifying the integration (see registry below). |
| `X-ZPL-Client-Version` | SemVer of the **calling package** (e.g. `1.0.1`, `4.1.1`). |

**Registry (examples; extend by adding new slugs here + in client code):**

| `X-ZPL-Client` | Owner |
|----------------|--------|
| `mcp` | zpl-engine-mcp |
| `cli` | zpl-engine-cli |
| `sdk-typescript` | `@zeropointlogic/sdk` |
| `sdk-python` | `zeropointlogic` PyPI |
| `sdk-csharp` | Reserved (Unity / .NET thin client — F2) |
| `gpt-action` | OpenAI Custom GPT Action |
| `telegram-bot` | @zpl_agent_bot |
| `discord-bot` | Future |
| `bookmarklet` | Viral one-liner |
| `gha` | GitHub Actions smoke / CI |

Custom forks **MAY** override `X-ZPL-Client` (e.g. `my-corp-bridge`) for internal attribution; `X-ZPL-Client-Version` should still reflect the deployed artifact version.

## Consequences

- Engine middleware can prefer these headers over UA parsing when present (E2 — separate timeline).
- Until E2 ships, proxies can log raw header values without DB schema changes.
- ADR [0001](./0001-engine-client-telemetry.md) remains the umbrella for DB + Axum work; **0002** is the canonical header names and client-type vocabulary (`sdk-ts` from early 0001 drafts is superseded by `sdk-typescript`).

## References

- TypeScript: `packages/typescript/src/client.ts`, `meta.ts`
- Python: `packages/python/zeropointlogic/client.py`
