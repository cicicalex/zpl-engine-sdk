# Exemple code (snippets) — ZPL în motoare

Fișiere **referință**, nu biblioteci compilate aici.

După ce modifici fișiere `.md` aici, în monorepo **SDK** rulează din rădăcina repo-ului `pwsh ./scripts/verify-docs-games.ps1` (același lucru face CI: workflow `Verify docs games`). În workspace cu `zpl-games/`, folosește `tools/sync-zpl-games-to-sdk.ps1` înainte de commit în `zpl-engine-sdk`.

| Fișier | Motor |
|--------|--------|
| [godot-server-snippet.md](./godot-server-snippet.md) | Godot 4 |
| [unity-httpclient-snippet.md](./unity-httpclient-snippet.md) | Unity (C# server) |
| [unreal-http-subsystem-sketch.md](./unreal-http-subsystem-sketch.md) | Unreal (C++) |
| [bevy-reqwest-snippet.md](./bevy-reqwest-snippet.md) | Bevy / Rust (`reqwest`) |
| [defold-http-snippet.md](./defold-http-snippet.md) | Defold (Lua `http.request`) |
| [web-typescript-bff-snippet.md](./web-typescript-bff-snippet.md) | Web TS / Phaser / Pixi / BFF |
| [gamemaker-gml-http-snippet.md](./gamemaker-gml-http-snippet.md) | GameMaker (GML) |
| [flame-dart-http-snippet.md](./flame-dart-http-snippet.md) | Flame / Flutter (Dart → BFF) |
| [roblox-httpservice-snippet.md](./roblox-httpservice-snippet.md) | Roblox (Luau `HttpService`) |
| [monogame-httpclient-note.md](./monogame-httpclient-note.md) | MonoGame / FNA → vezi Unity |
| [renpy-http-bridge-snippet.md](./renpy-http-bridge-snippet.md) | Ren'Py (`renpy.fetch` / BFF) |
| [love2d-bridge-snippet.md](./love2d-bridge-snippet.md) | Love2D (BFF / TLS) |
| [dotnet-maui-http-note.md](./dotnet-maui-http-note.md) | .NET MAUI → vezi Unity |
| [redot-godot-note.md](./redot-godot-note.md) | Redot → vezi Godot 4 |
| [construct3-ajax-bff-snippet.md](./construct3-ajax-bff-snippet.md) | Construct 3 (AJAX → BFF) |
| [haxe-openfl-http-snippet.md](./haxe-openfl-http-snippet.md) | Haxe / OpenFL / Heaps → BFF |
| [gdevelop-fetch-bff-snippet.md](./gdevelop-fetch-bff-snippet.md) | GDevelop 5 → BFF |
| [fusion-clickteam-bff-snippet.md](./fusion-clickteam-bff-snippet.md) | Clickteam Fusion → BFF |
| [unreal-lyra-packaging-note.md](./unreal-lyra-packaging-note.md) | Unreal Lyra + dedicated server |
| [stencyl-http-bff-snippet.md](./stencyl-http-bff-snippet.md) | Stencyl → BFF |
| [godot-web-export-bff-note.md](./godot-web-export-bff-note.md) | Godot export Web → BFF |
| [pico8-limit-note.md](./pico8-limit-note.md) | PICO-8 — limitări rețea |
| [stride-httpclient-note.md](./stride-httpclient-note.md) | Stride (C#) → vezi Unity |
| [w4-godot-note.md](./w4-godot-note.md) | Godot comercial / W4 → același flux |
| [o3de-http-cpp-note.md](./o3de-http-cpp-note.md) | O3DE (C++ server / Gem) |
| [cryengine-http-cpp-note.md](./cryengine-http-cpp-note.md) | CryEngine / Lumberyard (C++) |
| [source2-server-http-note.md](./source2-server-http-note.md) | Source 2 (dedicated server) |
| [custom-engine-c-http-note.md](./custom-engine-c-http-note.md) | Motor propriu C/C++ |

Index documentație: [../README.md](../README.md).
