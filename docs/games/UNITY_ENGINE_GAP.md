# Unity — ce acoperă `UNITY.md` vs ce lipsește în `docs/games`

Sursă canonică arhitectură: [../UNITY.md](../UNITY.md) (F1). Acest fișier evită duplicarea și marchează **gap-uri** utile pentru implementatori.

| Subiect | În `UNITY.md`? | Notă / gap în docs locale |
|---------|----------------|----------------------------|
| Server authoritative | Da | Repetat scurt în [INTEGRATIONS_UNITY_GODOT_UNREAL.md](./INTEGRATIONS_UNITY_GODOT_UNREAL.md) |
| Fără `zpl-core` în client | Da | Aliniat cu [AGENT_NOTES.md](./AGENT_NOTES.md) |
| `HttpClient` / `UnityWebRequest` | Da | Snippet extins: [examples/unity-httpclient-snippet.md](./examples/unity-httpclient-snippet.md) |
| `POST /compute`, JSON body | Da | Corpul exact = vezi [openapi.yaml](../openapi.yaml) |
| Headere ADR 0002 (`X-ZPL-Client`) | Da | Exemplu comentat în snippet; registru în ADR |
| OpenAPI codegen C# | Da (preview) | [OPENAPI_GENERATOR.md](../OPENAPI_GENERATOR.md) |
| Pachet C# oficial (F2) | Explicit backlog | **Gap produs:** nu există încă pachet npm/UPM susținut — folosești HTTP manual sau codegen |
| asmdef server-only | Nu în UNITY.md | **Gap:** recomandare în snippet — separă assembly server |
| Paritate erori cu Godot/Unreal | Parțial | Vezi [INTEGRATIONS_UNITY_GODOT_UNREAL.md](./INTEGRATIONS_UNITY_GODOT_UNREAL.md) secțiunea **HTTP comun** |
| Exemple scene Unity | Nu | **Gap viitor:** repo șablon Faza B — [TEMPLATE_REPOS_PHASE_B.md](./TEMPLATE_REPOS_PHASE_B.md) |

## Legături rapide

- [UNITY.md](../UNITY.md)
- [SDK_VS_HTTP.md](./SDK_VS_HTTP.md)
- [DEMO_CATALOG.md](./DEMO_CATALOG.md) — echivalent web pentru „observații → scor”
