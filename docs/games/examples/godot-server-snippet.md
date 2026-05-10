# Godot 4.x — apel ZPL de pe server (GDScript)

Scop: **doar** procesul autoritar (dedicated server / host) face HTTPS către ZPL; jucătorii nu văd cheia API.

## Nod recomandat

- Un `Node` (ex. `ZplServerBridge`) adăugat scenei **server** sau încărcat doar când `multiplayer.is_server()` este adevărat.
- Folosește **`HTTPRequest`** (Godot 4) — rulează pe main thread; pentru volume mare poți coadă cereri serial sau muta într-un mic serviciu lateral.

## Pseudocod (GDScript)

```gdscript
# Pe server: pliază observațiile tale într-un payload JSON compatibil cu API-ul tău
# (ex. scale, value, runs pentru demo BFF — sau matrice/samples pentru compute complet).
# NU pune cheia în export_presets.cfg, nu o pune în scene exportate pe mobil.

extends Node

const ZPL_URL := "https://engine.zeropointlogic.io/compute"  # sau proxy-ul tău
@export var zpl_api_key: String = ""  # încarcă din env / fișier server-only, NICIODATĂ în client build

func _ready() -> void:
    if not multiplayer.is_server():
        queue_free()
        return
    # alternativ: if not multiplayer.has_multiplayer_peer(): ...

func request_neutrality_score(value: float, runs: int, scale: int) -> void:
    var http := HTTPRequest.new()
    add_child(http)
    http.request_completed.connect(_on_zpl_done.bind(http))
    var body := JSON.stringify({"value": value, "runs": runs, "scale": scale})
    var headers := PackedStringArray([
        "Content-Type: application/json",
        "Authorization: Bearer %s" % zpl_api_key,
        # "X-ZPL-Client: your-channel",
        # "X-ZPL-Client-Version: 1.0.0",
    ])
    var err := http.request(ZPL_URL, headers, HTTPClient.METHOD_POST, body)
    if err != OK:
        push_error("ZPL request failed to start: %s" % err)

func _on_zpl_done(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray, http: HTTPRequest) -> void:
    http.queue_free()
    if result != HTTPRequest.RESULT_SUCCESS or code < 200 or code >= 300:
        push_warning("ZPL HTTP %s" % code)
        return
    var text := body.get_string_from_utf8()
    var data = JSON.parse_string(text)
    if typeof(data) != TYPE_DICTIONARY:
        return
    # Folosește doar câmpuri publice: ain, ain_status, tokens_used, etc. — vezi contract API.
```

## Capcane export (Android / iOS / desktop)

1. **`@export var zpl_api_key`** — dacă lasă gol în editor dar îl setezi în instanță pe server dedicat, e OK; **nu** împacheta aceeași scenă cu cheie în build-ul client PvP.
2. **Export presets** — orice `feature` / `environment` care injectează chei în binary-ul jucătorului = risc; preferă **variabile de mediu** pe mașina care rulează serverul.
3. **`HTTPRequest` pe client** — chiar fără cheie, nu expune endpoint-ul intern care bypass-uieste rate limits; clientul apelează **serverul tău de joc**, care apelează ZPL.

## Legături

- [INTEGRATIONS_UNITY_GODOT_UNREAL.md](../INTEGRATIONS_UNITY_GODOT_UNREAL.md) — context multiplayer.
- Erori / retry: secțiunea **Godot: HTTP errors** din același fișier.
