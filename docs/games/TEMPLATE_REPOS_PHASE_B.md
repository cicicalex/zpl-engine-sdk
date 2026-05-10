# Faza B (opțional): repo-uri șablon `zpl-integration-*`

Când snippet-urile din [examples/](./examples/) sunt suficiente pentru echipă, poți extrage **repo-uri mici** per motor, fiecare cu:

- README cu link către [openapi.yaml](../openapi.yaml)
- Un singur flux: „observații → JSON → HTTPS → parse public fields”
- **Fără** chei în repo; `.env.example` fără valori secrete
- CI minimal (format + build) opțional

## Nume sugerate

| Repo | Conținut minimal |
|------|------------------|
| `zpl-integration-godot` | Godot 4 proiect gol + autoload server-only + script din [examples/godot-server-snippet.md](./examples/godot-server-snippet.md) |
| `zpl-integration-unity` | asmdef server + exemplu din [examples/unity-httpclient-snippet.md](./examples/unity-httpclient-snippet.md) |
| `zpl-integration-unreal` | modul C++ minimal + fișiere din [examples/unreal-http-subsystem-sketch.md](./examples/unreal-http-subsystem-sketch.md) |

Acest document **nu** creează repo-urile — doar le definește ca backlog executabil când alegi explicit Faza B.
