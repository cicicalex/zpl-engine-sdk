# Gen gameplay → motoare / integrare (ghid D3)

**Nu este o normă de produs** — doar o mapare de lucru: majoritatea genurilor folosesc **același** flux HTTP server-side; diferența e unde rulezi simularea agregată înainte de apel.

| Gen (exemple din demo-uri) | ZPL ca strat de decizie (exemplu) | Motor adesea folosit | Pattern integrare |
|----------------------------|-----------------------------------|----------------------|-------------------|
| Fairness / RNG (dice, coin, rng-validator) | Drift față de uniform / așteptat | Oricare | Batch sau la sfârșitul run-ului |
| Loot / gacha / slots | Neutralitate distribuție rare vs advertised | Unity, Godot, custom | Server rolls + ZPL pe histogramă |
| PvP / arena / card / BR | Pattern combat / win equity | Unreal, Unity | Dedicated server apelează ZPL |
| Racing | Distribuție finish poziții | Unity, Godot | Run-uri agregate |
| Economy / crafting / MMO | Stabilitate flux resurse / drop | Oricare + backend Node | SDK TS/Python pe microserviciu e OK |
| Matchmaking | Echilibru skill / snake draft | Backend + orice client | ZPL pe matricea de matchup |

## Concluzie

„Genul” alege **ce observații** construiești; **motorul** alege **limbajul** glue-ului. Nu trebuie un SDK diferit per gen — doar per **stack** (vezi [INTEGRATIONS_UNITY_GODOT_UNREAL.md](./INTEGRATIONS_UNITY_GODOT_UNREAL.md)). Pentru **Rust ECS** (Bevy), **Lua** (Defold, Love2D), **browser** (TypeScript + BFF), **GML**, **Dart/Flutter** (Flame), **Roblox**, **MonoGame/FNA**, **Stride** / **Flax** (C#), **Ren'Py**, **.NET MAUI**, **Redot** / **Godot** (incl. **W4** comercial, Web WASM), **Construct 3** (AJAX), **Haxe/OpenFL/Heaps**, **GDevelop**, **Clickteam Fusion**, **Stencyl**, **Unreal Lyra** (server), **O3DE** / **CryEngine** / **Source 2** / **id Tech** / **Serious Engine** (C++ dedicat), **motor propriu C/C++** sau **PICO-8** (limitări), vezi [examples/](./examples/).
