# Changelog

All notable changes to the ZPL Engine SDK monorepo are documented here.

Versioning: **TypeScript** and **Python** package versions in `packages/*` should stay aligned for the same API contract. **zpl-engine-mcp** is released separately from [github.com/cicicalex/zpl-engine-mcp](https://github.com/cicicalex/zpl-engine-mcp); note compatible engine URLs in MCP release notes.

## [2.1.0] - 2026-07-31

Applies to both `@zeropointlogic/sdk` (npm) and `zeropointlogic` (PyPI).

### Added
- `analyze()` carries `inputOnes` / `input_ones`, `cells` and `degenerate`.
  At every even dimension the engine's family verdicts are identical for an
  all-zeros and an all-ones matrix, so without these the two most opposite
  inputs a caller can send came back indistinguishable. Optional: an engine
  predating them sends nothing, and absent stays absent rather than becoming 0.
- Both READMEs explain `p_output` - the balance the engine measured, where
  0.500 is equilibrium - and state that `ain` is symmetric about equilibrium
  and therefore cannot say which side a reading falls on.

### Changed
- The two SDKs described the same reading differently. TypeScript used bands
  0.95/0.8/0.7/0.6/0.4/0.2 and Python used 0.85/0.70/0.55/0.40/0.25; neither
  matched the engine. At ain 0.87 TypeScript said "Excellent neutrality" and
  Python said "Perfectly Neutral" while the engine reports NEUTRAL. Both now
  use the engine's boundaries and identical wording, and each test suite
  cross-checks the other language's source.

## [1.0.4] - 2026-05-11

### Python (`zeropointlogic`)

- **Packaging:** `license = "MIT"` (SPDX string) instead of deprecated `license = { text = "MIT" }` for setuptools 77+; removed redundant `License :: OSI Approved :: MIT License` classifier (license field is canonical).

### TypeScript (`@zeropointlogic/sdk`)

- Version bump only — **parity** with Python `1.0.4` (no API changes).

## [1.0.3] - 2026-05-11

### TypeScript (`@zeropointlogic/sdk`)

- Fix npm metadata: `repository`, `homepage`, and `bugs` now point to [github.com/cicicalex/zpl-engine-sdk](https://github.com/cicicalex/zpl-engine-sdk) (previous `zeropointlogic/sdk-ts` URL was 404).

### Python (`zeropointlogic`)

- Fix PyPI `[project.urls]`: Homepage, Repository, Issues, etc. → same monorepo `cicicalex/zpl-engine-sdk`.

## [1.0.2] - 2026-05-11

### TypeScript (`@zeropointlogic/sdk`)

- Send `X-ZPL-Client` (default `sdk-typescript`) and `X-ZPL-Client-Version` (package semver) on every request per [ADR 0002](docs/adr/0002-x-zpl-client-headers.md); optional `xZplClient` / `xZplClientVersion` on `ZPLClientConfig`.
- Export `ZPL_SDK_CLIENT_TYPE`.

### Python (`zeropointlogic`)

- Same ADR 0002 headers with defaults `sdk-python` and package `__version__`; optional `x_zpl_client` / `x_zpl_client_version` on `BaseZPLClient`.
- Export `ZPL_SDK_CLIENT_TYPE`.

### Docs / CI

- GitHub Pages workflow for public `docs/openapi.yaml`; [GITHUB_PAGES.md](docs/GITHUB_PAGES.md), [UNITY.md](docs/UNITY.md), CI `openapi_smoke` (Docker validate + Go/Java generate).
- OpenAPI spec documents optional `X-ZPL-Client` parameters on `/plans`, `/compute`, `/sweep`.

## [1.0.1] - 2026-05-10

### TypeScript (`@zeropointlogic/sdk`)

- Normalize engine `snake_case` compute responses (`p_output`, `ain_status`, `tokens_used`, `compute_ms`).
- `Authorization: Bearer` + `X-API-Key` on requests; Mozilla-compatible `User-Agent` for Cloudflare.
- `parseEngineHttpError` for HTML / Cloudflare error bodies.
- Tests: `normalizeEngineComputeResult` + redaction helper.

### Python (`zeropointlogic`)

- `compute_result_from_engine_dict` for response normalization; optional `ain_status`, `compute_ms` on `ComputeResult`.
- `parse_engine_http_error` for non-JSON error responses.
- `Authorization: Bearer` + browser-like `User-Agent`; `version.py` for package version.

### Docs / repo

- Monorepo root README, OpenAPI skeleton, Postman notes, CI workflow, ADR for client telemetry.

## [1.0.0] - prior

Initial published SDKs (pre-monorepo paths under `Proiecte/`).
