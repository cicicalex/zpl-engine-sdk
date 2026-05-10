# GitHub Pages — public OpenAPI URL

This folder (`zpl-engine-sdk/docs/`) is deployed as a **static site** by the workflow
[`.github/workflows/openapi-pages.yml`](../.github/workflows/openapi-pages.yml)
when this SDK tree is the repository root (or adjust paths if nested inside a larger monorepo).

## One-time setup (repository admin)

1. On GitHub: **Settings → Pages → Build and deployment**.
2. Under **Source**, choose **GitHub Actions** (not “Deploy from a branch”).
3. Merge the workflow to `main` and push, or run **Actions → OpenAPI Pages → Run workflow**.

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

## Game integration docs (markdown)

Markdown for Unity / Godot / Unreal, demo catalog, and snippets lives in **[docs/games/](https://github.com/cicicalex/zpl-engine-sdk/tree/main/docs/games)** on `main`. It is not part of the Pages OpenAPI artifact unless you extend the workflow; use the GitHub tree or raw links for sharing.
