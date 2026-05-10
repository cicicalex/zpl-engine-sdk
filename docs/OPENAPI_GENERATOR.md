# openapi-generator (optional)

Generate clients in **Java, Go, Ruby, PHP, C#, Swift**, etc. from [openapi.yaml](./openapi.yaml).

## CI verification (source of truth)

On every push/PR that touches `zpl-engine-sdk/**`, GitHub Actions runs job **`openapi_smoke`** in
[`.github/workflows/zpl-engine-sdk-ci.yml`](../../.github/workflows/zpl-engine-sdk-ci.yml):

1. `openapi-generator-cli validate -i …/docs/openapi.yaml`
2. `generate` with `-g go` → `zpl-engine-sdk/generated-ci-smoke/go` (ignored by git)
3. `generate` with `-g java` → `zpl-engine-sdk/generated-ci-smoke/java` (ignored by git)
4. Asserts `README.md` plus at least one `.go` / `.java` file exist.

If local Docker differs from CI, trust the **green CI log** as the verified end-to-end run.

## Prerequisite

Docker (recommended) or a local `openapi-generator-cli` install.

## Docker — validate spec

From the **monorepo root** (`C:\Dev`):

```bash
docker run --rm -v "$PWD:/local" openapitools/openapi-generator-cli validate \
  -i /local/zpl-engine-sdk/docs/openapi.yaml
```

**Expected (success):** last lines similar to:

```text
Validating spec (/local/zpl-engine-sdk/docs/openapi.yaml)
No validation issues found.
```

From **inside** `zpl-engine-sdk/` only (Linux / macOS / WSL):

```bash
docker run --rm -v "${PWD}:/local" openapitools/openapi-generator-cli validate \
  -i /local/docs/openapi.yaml
```

**Windows PowerShell** (Docker Desktop path mount):

```powershell
docker run --rm -v "${PWD}:/local" openapitools/openapi-generator-cli validate `
  -i /local/docs/openapi.yaml
```

Run from directory `C:\Dev\zpl-engine-sdk` so `${PWD}` resolves correctly.

## Docker — generate Go (enterprise / services)

From monorepo root:

```bash
mkdir -p zpl-engine-sdk/generated/go
docker run --rm -v "$PWD:/local" openapitools/openapi-generator-cli generate \
  -i /local/zpl-engine-sdk/docs/openapi.yaml \
  -g go \
  -o /local/zpl-engine-sdk/generated/go \
  --additional-properties=packageName=zplengine
```

**Expected:** console ends with `INFO o.o.codegen.DefaultGenerator - writing file …` for multiple files; on disk:

- `generated/go/README.md`
- `generated/go/go.mod` (generator version dependent)
- Several `*.go` files (API + client)

## Docker — generate Java (enterprise / JVM)

From monorepo root:

```bash
mkdir -p zpl-engine-sdk/generated/java
docker run --rm -v "$PWD:/local" openapitools/openapi-generator-cli generate \
  -i /local/zpl-engine-sdk/docs/openapi.yaml \
  -g java \
  -o /local/zpl-engine-sdk/generated/java \
  --additional-properties=invokerPackage=io.zeropointlogic.engine,apiPackage=io.zeropointlogic.engine.api,modelPackage=io.zeropointlogic.engine.model
```

**Expected:** `generated/java/README.md`, `generated/java/pom.xml`, and `generated/java/src/main/java/...` populated with API and model classes.

## One-liners from `zpl-engine-sdk/` only (PowerShell)

Replace `csharp` / `ruby` / etc. as needed:

```powershell
docker run --rm -v "${PWD}:/local" openapitools/openapi-generator-cli generate `
  -i /local/docs/openapi.yaml `
  -g csharp `
  -o /local/generated/csharp
```

## Output policy

- Default: add `generated/` to `.gitignore` and **do not** commit huge trees unless you intend to maintain them.
- CI smoke output goes to `generated-ci-smoke/` (also gitignored).
- For Unity: generate **C#** into a separate repo or Unity `Packages/` folder and commit only reviewed output (F2 / separate mandate; see [UNITY.md](./UNITY.md)).

## Postman

You can also import `openapi.yaml` directly in Postman (**Import → Raw text**). See [postman/README.md](./postman/README.md).
