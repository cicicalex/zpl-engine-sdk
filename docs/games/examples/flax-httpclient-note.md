# Flax Engine (C# / .NET) — `HttpClient` pe **server**

**Flax** este un motor **C#** peste **.NET** (runtime similar celui folosit de Unity/Stride). Pentru ZPL: folosește **`System.Net.Http.HttpClient`** (sau abstracții tale) **doar** în cod care rulează pe **dedicated server**, într-un **plugin server-only**, sau într-un **BFF** .NET lângă sesiune — la fel ca [unity-httpclient-snippet.md](./unity-httpclient-snippet.md) și [stride-httpclient-note.md](./stride-httpclient-note.md).

## Unde scrii codul

- **Assembly / script** marcat sau deploy-at **numai** în build-ul de server (headless / dedicated), nu în pachetul client descărcat de jucători.
- **Editor scripts** care rulează la tine în CI pot apela ZPL cu cheie — nu împacheta aceeași cheie în **Game** build pentru distribuție publică.

## Referințe în repo

- [stride-httpclient-note.md](./stride-httpclient-note.md) — același stack C# / `HttpClient`.
- [monogame-httpclient-note.md](./monogame-httpclient-note.md) — familie .NET.

Coduri HTTP: [INTEGRATIONS_UNITY_GODOT_UNREAL.md](../INTEGRATIONS_UNITY_GODOT_UNREAL.md#http-comun-unity-godot-unreal).

OpenAPI: [openapi.yaml](../../openapi.yaml).
