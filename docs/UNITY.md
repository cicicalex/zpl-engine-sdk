# Unity and the ZPL Engine (architecture)

This document is for **Unity engineers** deciding how to integrate ZPL AIN / stability analysis. It describes **F1 — architecture only**. A thin C# client package (F2) is a separate mandate.

## Server authoritative (required)

- **AIN runs on the ZPL Engine** over HTTPS. The engine holds API keys, quotas, and rate limits.
- **Unity does not embed** the mathematical engine, WASM rebuilds of proprietary cores, or copied `zpl-core` logic. That matches product policy (trade secret, server-side certification).
- **Unity is a consumer** of the same public HTTP API documented in [openapi.yaml](./openapi.yaml).

## Typical integration pattern

1. **Secrets:** Keep `ZPL_API_KEY` on a **game server** or backend you control (same as any mobile game with a paid API). Avoid shipping long-lived keys in client builds players can extract.
2. **Transport:** Server uses `HttpClient` (or `UnityWebRequest` on a headless worker) → `POST /compute` with JSON body (`matrix`, `samples`, etc.).
3. **Gameplay:** Clients receive **derived** results only (e.g. `ain`, `ain_status`, `tokens_used` as allowed by your UX). Do not log raw engine internals.

## When Unity talks to the engine directly (prototypes / tools)

- Use **`HttpClient`** or **`UnityWebRequest`** against `https://engine.zeropointlogic.io` (or your proxy).
- Set **browser-like `User-Agent`** and the **ADR 0002** headers (`X-ZPL-Client`, `X-ZPL-Client-Version`) once your channel slug is registered (e.g. `sdk-csharp` reserved for a future package, or a custom slug for an internal tool).
- Respect timeouts and retries; surface “data unavailable” if the API fails — **no fabricated scores**.

## OpenAPI and codegen (F2 preview)

- OpenAPI-driven **C#** generation is optional; see [OPENAPI_GENERATOR.md](./OPENAPI_GENERATOR.md). Review generated code before shipping.
- **F2 (C# SDK package)** is backlog until explicitly approved — do not treat generated stubs as a supported product without that mandate.

## Related

- [ADR 0001](./adr/0001-engine-client-telemetry.md) — future `usage_log` attribution on the engine (Alex / Rust).
- [ADR 0002](./adr/0002-x-zpl-client-headers.md) — `X-ZPL-Client` registry shared across SDKs and channels.
- [games/README.md](./games/README.md) — docs comune jocuri (Godot/Unreal snippets, catalog demo, gap-uri vs acest fișier în `games/UNITY_ENGINE_GAP.md`).
