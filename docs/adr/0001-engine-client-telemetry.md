# ADR 0001: Engine client telemetry (MCP vs SDK)

## Status

Proposed — **implementation on the Rust engine requires Alex** (see [AGENTS.md](../../../AGENTS.md)).

## Context

We need to attribute token usage and traffic to client families: MCP, TypeScript SDK, Python SDK, Postman, GitHub Actions, Unity, dashboard, etc.

## Decision (target architecture)

1. **Clients** send:
   - A **distinct `User-Agent`** string per product (already partially done for MCP and SDKs).
   - Explicit headers (contract in [ADR 0002](./0002-x-zpl-client-headers.md); SDK implements from 0002):
     - `X-ZPL-Client` — registry of slugs (e.g. `sdk-typescript`, `sdk-python`, `mcp`, `cli`).
     - `X-ZPL-Client-Version` — SemVer of the calling package (e.g. `4.1.0`, `1.0.1`).

2. **Engine** (Axum middleware + persistence):
   - Parse `User-Agent`, `X-ZPL-Client`, `X-ZPL-Client-Version` on each authenticated request.
   - Store `client_type`, `client_version` (nullable), `api_key_id`, `endpoint`, `tokens_used`, `timestamp` in `usage_log` (or equivalent table).

3. **Dashboard** (ZPL Main): aggregate queries — separate blueprint / mandate.

## Consequences

- Requires DB migration and Rust changes — **not** in the SDK-only repo alone.
- Until shipped, use **Cloudflare / proxy logs** filtered by `User-Agent` as a partial substitute.

## References

- MCP UA pattern: [mcp/engine-mcp/src/setup.ts](../../../mcp/engine-mcp/src/setup.ts)
- SDK UA pattern: `zpl-engine-sdk/packages/typescript`, `packages/python`
