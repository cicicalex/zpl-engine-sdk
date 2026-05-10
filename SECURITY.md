# Security policy

## Supported versions

We support the latest **minor** release of `@zeropointlogic/sdk` (npm) and `zeropointlogic` (PyPI) published from this monorepo. Older versions may not receive backports.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for undisclosed security problems.

- Email: use the contact on [zeropointlogic.io](https://zeropointlogic.io) or the maintainer address in `pyproject.toml` / npm package metadata.
- Include: affected package (`sdk-ts`, `sdk-py`, `mcp`), version, reproduction steps, and impact. Do not attach real API keys.

## Scope

- **In scope:** API key handling in SDKs/MCP, TLS usage, error handling that might leak secrets, dependency vulnerabilities in this repo’s manifests.
- **Out of scope for this repo:** Rust engine internals (`zpl-core`), production server configuration — report engine issues through the same contact with clear separation.

## API keys

- Never commit `zpl_` keys or `.env` files.
- Rotate keys if they appear in logs, CI output, or chat exports.
- For CI, use GitHub **encrypted secrets** only.

## MCP local config

`zpl-engine-mcp setup` writes `~/.zpl/config.toml` with restrictive permissions where the OS allows it. Treat that file like a password store.
