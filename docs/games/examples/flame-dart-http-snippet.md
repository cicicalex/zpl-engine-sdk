# Flame / Flutter (Dart) — `http` sau Dio către BFF

Scop: jocuri **2D/Flutter** (Flame) rulează adesea pe **mobil și web**; cheia ZPL **nu** intră în `assets/`, în `--dart-define` public sau în repo. La fel ca [web-typescript-bff-snippet.md](./web-typescript-bff-snippet.md): clientul vorbește cu **API-ul tău**, iar backend-ul apelează ZPL.

## Pattern recomandat

1. **Flutter:** `http.post` / `dio` către `https://api.tauproject.ro/zpl-bridge` (fără header ZPL în app).
2. **Bridge** (Cloud Run, Firebase Functions, etc.) adaugă `Authorization: Bearer …` și face `POST` la `engine.zeropointlogic.io/compute`.

## Schiță Dart (client — fără cheie ZPL)

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

Future<Map<String, dynamic>?> requestZplViaBff(
    Map<String, Object?> payload) async {
  final uri = Uri.parse('https://api.example.com/zpl-bridge'); // același contract JSON
  final res = await http.post(
    uri,
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode(payload),
  );
  if (res.statusCode < 200 || res.statusCode >= 300) return null;
  return jsonDecode(res.body) as Map<String, dynamic>;
}
```

## Capcane Flame / Flutter

- **`--dart-define=ZPL_KEY=...` în CI public:** vizibil în istoric; folosește doar pe **build server-side** dacă absolut necesar, altfel exclusiv BFF.
- **Web target (CanvasKit):** CORS pe BFF; nu expune cheia în `index.html`.
- **429 / 401 / 402:** propagă mesajul UX fără a inventa `ain` (vezi [INTEGRATIONS_UNITY_GODOT_UNREAL.md](../INTEGRATIONS_UNITY_GODOT_UNREAL.md#http-comun-unity-godot-unreal)).

OpenAPI (contract corp): [openapi.yaml](../../openapi.yaml).
