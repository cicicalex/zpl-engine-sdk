# GitHub Pages — public OpenAPI URL

This folder (`zpl-engine-sdk/docs/`) is deployed as a **static site** by the workflow
[`.github/workflows/zpl-engine-sdk-openapi-pages.yml`](../../.github/workflows/zpl-engine-sdk-openapi-pages.yml)
in the parent monorepo (`C:\Dev`).

## One-time setup (repository admin)

1. On GitHub: **Settings → Pages → Build and deployment**.
2. Under **Source**, choose **GitHub Actions** (not “Deploy from a branch”).
3. Merge the workflow to `main` and push, or run **Actions → zpl-engine-sdk OpenAPI Pages → Run workflow**.

After the first successful run, the site URL is shown in the job summary and under **Settings → Pages**.

## Stable OpenAPI URL

| If your GitHub repo is named… | Public spec (example owner `cicicalex`) |
|-------------------------------|-------------------------------------------|
| `zpl-engine-sdk` | `https://cicicalex.github.io/zpl-engine-sdk/openapi.yaml` |
| `Dev` (or any other name) | `https://cicicalex.github.io/<repo>/openapi.yaml` |

Replace `<repo>` with the **repository** slug (not the folder name). The path is always `/openapi.yaml` at site root because the artifact is this `docs/` directory.

## Verify

```bash
curl -fsSL "https://cicicalex.github.io/zpl-engine-sdk/openapi.yaml" | head -n 5
```

Expect `openapi: 3.0.3` (or your spec version) in the first lines.

## Standalone `zpl-engine-sdk` mirror

If you maintain a **dedicated** GitHub repo whose root is only this SDK tree, copy `docs/` and `.github/workflows/` to that repo and set the workflow `path:` to `docs` instead of `zpl-engine-sdk/docs`.
