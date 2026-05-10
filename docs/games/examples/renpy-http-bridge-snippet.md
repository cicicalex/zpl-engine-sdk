# Ren'Py — apel către **BFF** (`renpy.fetch` / Python), fără cheie în build

Scop: jocurile vizuale Ren'Py distribuite ca **`.zip` / Steam** nu trebuie să conțină cheia ZPL în scripturi `rpy` vizibile sau în `archive.rpa` ușor de extras. Modelul sigur: **BFF HTTPS**; motorul apelează doar URL-ul tău.

## Ren'Py 8+ — `renpy.fetch` (async-friendly)

```renpy
label call_zpl_bridge:
    $ payload = {"value": 0.5, "runs": 1000, "scale": 8}
    $ resp = renpy.fetch(
        "https://api.example.com/renpy-zpl",
        method="POST",
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    # Forma lui `resp` depinde de versiunea Ren'Py (ex. atribute .status / .text sau alt contract).
    # Dacă nu e succes HTTP, nu inventa AIN — vezi documentația oficială `renpy.fetch`.
    "Analiză terminată (verifică manual parsing-ul JSON pe versiunea ta)."
    return
```

Verifică în **documentația versiunii** tale Ren'Py semnătura exactă a `renpy.fetch` și modul de citire a codului HTTP / corpului răspunsului.

## Alternativă: microserviciu Python

- Rulezi **Node/Python cu SDK** lângă build-ul de dezvoltare; Ren'Py apelează `http://127.0.0.1:…` doar în **dev**; în producție doar HTTPS către BFF public.

## Capcane

- **`init python:` cu `requests` + cheie în fișier .rpy:** risc de leak în build; folosește BFF.
- **Mod developer:** dezactivează shortcut-uri care sar peste verificări de rețea în release.
- **Coduri HTTP:** vezi [INTEGRATIONS_UNITY_GODOT_UNREAL.md](../INTEGRATIONS_UNITY_GODOT_UNREAL.md#http-comun-unity--godot--unreal).

OpenAPI: [openapi.yaml](../../openapi.yaml).
