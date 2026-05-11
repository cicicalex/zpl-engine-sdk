# Stride (C# / .NET) — `HttpClient` ca Unity / MonoGame

**Stride** (fost Xenko) este un motor **C# / .NET**. Pentru apeluri HTTPS către ZPL sau către **BFF**, folosește același model ca **Unity headless** sau **MonoGame**: **`System.Net.Http.HttpClient`**, cheia doar pe **proces server** sau în **BFF**, nu în build-ul client distribuit.

## Unde scrii codul

- **Script async** într-un serviciu de joc / sistem care rulează **doar pe server** (sau într-un **worker** .NET lângă Stride), similar conceptului `HttpClient` din [unity-httpclient-snippet.md](./unity-httpclient-snippet.md).
- **Clientul** primește doar rezultate deja agregate (verdict, tier) prin RPC / mesaje tale de rețea.

## Referințe în repo

- [monogame-httpclient-note.md](./monogame-httpclient-note.md) — aceeași familie .NET + `HttpClient`.
- Coduri HTTP: [INTEGRATIONS_UNITY_GODOT_UNREAL.md](../INTEGRATIONS_UNITY_GODOT_UNREAL.md#http-comun-unity-godot-unreal).

OpenAPI: [openapi.yaml](../../openapi.yaml).
