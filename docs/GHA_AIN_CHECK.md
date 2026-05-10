# GitHub Action: ZPL Engine AIN check

Workflow file (repo root): [`.github/workflows/zpl-engine-ain-check.yml`](../../.github/workflows/zpl-engine-ain-check.yml)

## Behaviour

- **Schedule:** daily `GET https://engine.zeropointlogic.io/health` (no secret).
- **Manual (`workflow_dispatch`):** optional second job **POST /compute** when input `run_compute` is `true` and repository secret **`ZPL_API_KEY`** is set.

## Setup

1. GitHub repo → **Settings → Secrets and variables → Actions**.
2. Add secret `ZPL_API_KEY` with a test key (`zpl_…`) that has quota for smoke calls.
3. **Actions** → **ZPL Engine AIN check** → **Run workflow** → enable `run_compute` if you want the POST step.

## CI for SDK code

Separate workflow: [`zpl-engine-sdk-ci.yml`](../../.github/workflows/zpl-engine-sdk-ci.yml) runs on changes under `zpl-engine-sdk/`.
