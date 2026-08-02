# Changelog

All notable changes to the ZPL Engine SDK monorepo are documented here.

Versioning: **TypeScript** and **Python** package versions in `packages/*` should stay aligned for the same API contract. **zpl-engine-mcp** is released separately from [github.com/cicicalex/zpl-engine-mcp](https://github.com/cicicalex/zpl-engine-mcp); note compatible engine URLs in MCP release notes.

## [Unreleased]

### Fixed
- **Python:** `max_retries` counted attempts, not retries. `max_retries=0` — a
  reasonable way to say "do not retry" — sent no request at all and returned
  `None`, which surfaced to the caller as `AttributeError: 'NoneType' object
  has no attribute 'get'` from the result parser. Measured with a counting
  transport: 0 requests. It now sends one.
- **Python:** the same off-by-one put the two SDKs out of step. With
  `max_retries=3` the Python client made three attempts where the TypeScript
  client makes four from the same number. Both now mean one attempt plus that
  many retries, matching the parameter's own name and documentation. Both the
  sync and async clients were affected and both are fixed; the connection-retry
  path is the only one this touches, since a timeout stays terminal.
- **Python:** neither request loop can end without returning or raising, so a
  future change to the bound fails loudly instead of handing back `None`.

## [2.1.0] - 2026-08-02

Applies to both `@zeropointlogic/sdk` (npm) and `zeropointlogic` (PyPI).

This entry was first drafted on 2026-07-31 and covered only the two sections
immediately below. Six more changes landed before the release actually went out
on 2026-08-02, including a fix to what error objects carry. They are recorded
under *Fixed* and *Packaging*; the date above is the day 2.1.0 was published.

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

### Fixed

Items below are marked with the package they apply to where they do not apply
to both. Verified against the published packages, not inferred from the
changes: a stub engine was made to echo credentials back in an error body on
five different status codes, and both clients were driven against it.

- **TypeScript: error objects carried the engine's reply verbatim.** The
  package shipped a redaction helper, documented it "for logs / echoed
  errors", exported it — and never called it. Measured against an engine that
  echoed a key back in an error body: `message` read "Invalid request" while
  `details` held the engine's text intact, API key and all. The reassuring
  generic message is what made it look handled; anyone logging the error object
  — the ordinary thing to do — wrote the secret into their logs. The helper now
  runs on what reaches the caller. Python was measured on the same five status
  codes and never carried the body into the exception, so there was nothing to
  fix there.
- **A rejected matrix was described as a shape the caller had not sent.** Both
  languages reported the rejection as though the input had been square, so
  somebody who sent three rows of four columns was told about a 3x3. The
  message now reports what actually arrived — how many rows, and how many
  columns the first one has.
- **Python raised the wrong error for a matrix of nulls.** The length check ran
  before the row-type check, so a list of `None` values produced a `TypeError`
  from inside the SDK rather than the validation error the caller can act on.
  The type check now runs first.
- **`isNeutral` / `biasLevel` contradicted the engine on the headline metric,**
  inside the same result object. At a reading the engine classifies as
  moderately biased, the object said neutral. The TypeScript client carried a
  second private copy of the thresholds that populated every result and had not
  been realigned with the exported helper; Python disagreed with itself, with
  one predicate calling a reading biased and another calling the same reading
  neutral. Both languages now take the classification the engine sent rather
  than re-deriving it, and the duplicate copy is gone rather than corrected —
  two copies of a threshold is how they drift.
- **The Python package could not be imported on the Python it advertises.**
  `requires-python` declares 3.9 and four modules used syntax that needs 3.10,
  so an install on the advertised floor failed at import.
- **TypeScript: the default timeout was exactly the engine's compute ceiling,**
  and half of its sweep ceiling. Equal to the server's own deadline is a coin
  flip over which side fires first, and losing it means the caller is billed
  for work they abandoned: the engine refunds when its own timeout fires, not
  when the client gives up. For sweep it was not a coin flip — the SDK gave up
  first every time. The default now sits past the slowest route, so the
  engine's refunding timeout is what arrives. A shorter deadline is still
  available to anyone who passes one deliberately. Python's default was already
  65 seconds, above both ceilings, and is unchanged.

### Packaging — TypeScript

- **A publish would have shipped a package with no code in it.** `files` ships
  `dist/`, `.gitignore` excludes it, and nothing built it at publish time — so
  from a clean clone the tarball was README, LICENSE and `package.json`, with
  `main` pointing at a file that was not there. It stayed invisible because the
  test script builds first, so any machine that had run the tests had a
  populated `dist/`. A prepublish build now runs.
- The TypeScript lockfile said 1.0.4 while the package publishes 2.1.0, the
  version bumps having been hand-edited. Corrected, and pinned by a test that
  reads the lock, the description and this changelog against `package.json`.

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
