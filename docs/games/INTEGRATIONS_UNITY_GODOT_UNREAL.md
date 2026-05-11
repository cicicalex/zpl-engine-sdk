# Motoare de joc — integrare ZPL (Unity, Godot, Unreal și altele)

## Cuprins rapid

- **Principii:** [Un contract](#un-contract-mai-multe-scrieri) · [Regulă de aur (server authoritative)](#regulă-de-aur-server-authoritative) · [Matrice motoare](#matrice-motoare-si-unde-scrii-apelul-zpl) · [HTTP comun (coduri)](#http-comun-unity-godot-unreal)
- **Motoare „mari” (snippet principal):** [Unity](#unity) · [Godot](#godot) · [Unreal](#unreal)
- **Toate snippet-urile și notele A–Z:** [examples/README.md](./examples/README.md)

## Un contract, mai multe „scrieri”

- **ZPL Engine** expune același **API HTTP** (JSON) indiferent de motor.
- **Fiecare motor** are propriul runtime, limbaj și uneori threading: integrarea nu e un singur fișier universal, ci **câte un strat de glue** (sau repo mic) per motor — Unity (C#), Godot (GDScript/C#), Unreal (C++), plus altele mai jos.
- **SDK-urile oficiale** TypeScript/Python sunt pentru **Node/Python**, nu „magia” care rulează în interiorul editorului Unity/Godot; acolo folosești **HTTP nativ** sau un client **generat din OpenAPI** / viitor pachet C# dedicat.

## Regulă de aur: **server authoritative**

- **Cheia API** (`zpl_u_…`) stă pe **backend-ul** tău (dedicated server, Cloud Run, PlayFab Cloud Script, etc.), **nu** în build-ul clientului descărcat de jucători.
- Clientul jocului primește doar **rezultatul derivat** (ex. verdict, tier, cooldown) pe canalul tău deja securizat (WebSocket, HTTPS la serverul de joc).

## Matrice motoare si unde scrii apelul ZPL

| Motor / platformă | Limbaje tipice pe server | Client HTTP obișnuit | Notă |
|-------------------|--------------------------|----------------------|------|
| **Unity** | C# (.NET / IL2CPP headless) | `HttpClient`, `UnityWebRequest` | Glue separat de Godot/Unreal. |
| **Godot** | GDScript, C# | `HTTPRequest`, uneori `HTTPClient` (C#) | Nod sau autoload **doar pe server** în multiplayer autoritar. |
| **Unreal** | C++ | `FHttpModule` / `IHttpRequest` | Subsystem sau GameMode **server**; Blueprint → endpoint propriu C++. |
| **Bevy** (Rust) | Rust | `reqwest`, `ureq` | Server ECS sau bin separat care apelează ZPL. |
| **Defold** | Lua | `http.request` | Din context server / serviciu extern cu cheia. |
| **GameMaker** | GML | `http_request` | Preferă job server sau extensie care nu expune cheia în client. |
| **Cocos** (Creator / etc.) | TypeScript / C++ / Lua | `fetch`, `XMLHttpRequest`, native HTTP | Poate folosi același pattern ca web BFF dacă ești în TS. |
| **MonoGame / FNA** | C# | `HttpClient` | La fel ca Unity; vezi [monogame-httpclient-note.md](./examples/monogame-httpclient-note.md). |
| **Ren'Py** | Python / Ren'Py DSL | `renpy.fetch`, BFF | Vezi [renpy-http-bridge-snippet.md](./examples/renpy-http-bridge-snippet.md); fără cheie în `.rpy` livrate. |
| **Love2D** | Lua | BFF / microserviciu | Vezi [love2d-bridge-snippet.md](./examples/love2d-bridge-snippet.md); TLS în Lua e sensibil. |
| **Phaser / Pixi / Vite** | TypeScript | `fetch` către **BFF** | Cheia doar pe server; vezi snippet web. |
| **Flame / Flutter** | Dart | `http` / `dio` → **BFF** | Mobil + web; fără cheie în `--dart-define` public. |
| **Roblox** | Luau | `HttpService:RequestAsync` → **BFF** pe allowlist | Cheia ZPL doar pe serverul tău, nu în experience. |
| **.NET MAUI** | C# | `HttpClient` | Vezi [dotnet-maui-http-note.md](./examples/dotnet-maui-http-note.md). |
| **Redot** | GDScript, C# | ca Godot | Vezi [redot-godot-note.md](./examples/redot-godot-note.md). |
| **Construct 3** | JavaScript (runtime) | **AJAX** → BFF | Vezi [construct3-ajax-bff-snippet.md](./examples/construct3-ajax-bff-snippet.md); CORS + domenii. |
| **Haxe / OpenFL / Heaps** | Haxe | `haxe.Http`, `fetch`, `URLRequest`, `hxd.net` | Vezi [haxe-openfl-http-snippet.md](./examples/haxe-openfl-http-snippet.md); JS vs native. |
| **GDevelop 5** | Evenimente / JS | extensii **Network** → BFF | Vezi [gdevelop-fetch-bff-snippet.md](./examples/gdevelop-fetch-bff-snippet.md). |
| **Clickteam Fusion 2.5+** | Evenimente | GET/POST / extensii → BFF | Vezi [fusion-clickteam-bff-snippet.md](./examples/fusion-clickteam-bff-snippet.md). |
| **Stencyl** | Haxe / blocuri | HTTP → BFF | Vezi [stencyl-http-bff-snippet.md](./examples/stencyl-http-bff-snippet.md). |
| **Godot (export Web)** | GDScript / WASM | `HTTPRequest` → BFF | Vezi [godot-web-export-bff-note.md](./examples/godot-web-export-bff-note.md). |
| **PICO-8** | Lua | rețea limitată | Vezi [pico8-limit-note.md](./examples/pico8-limit-note.md) — de obicei BFF în afara cartușului. |
| **Stride** | C# | `HttpClient` | Vezi [stride-httpclient-note.md](./examples/stride-httpclient-note.md). |
| **Flax** | C# | `HttpClient` pe **dedicated** / server-only | Vezi [flax-httpclient-note.md](./examples/flax-httpclient-note.md). |
| **O3DE** | C++ | HTTP pe **server** / Gem | Vezi [o3de-http-cpp-note.md](./examples/o3de-http-cpp-note.md). |
| **CryEngine / Lumberyard** | C++ | HTTP pe **server** dedicat | Vezi [cryengine-http-cpp-note.md](./examples/cryengine-http-cpp-note.md). |
| **Source 2** (Valve) | C++ | HTTP pe **SRCDS** / dedicat | Vezi [source2-server-http-note.md](./examples/source2-server-http-note.md). |
| **id Tech** (id Software) | C++ | HTTP pe **dedicated** / bin server | Vezi [idtech-dedicated-server-http-note.md](./examples/idtech-dedicated-server-http-note.md). |
| **Serious Engine** (Croteam) | C++ (uneori AngelScript pe server) | HTTP pe **dedicated** / serviciu lângă server | Vezi [serious-engine-http-cpp-note.md](./examples/serious-engine-http-cpp-note.md). |
| **Motor propriu (C/C++)** | C / C++ | `libcurl` / daemon | Vezi [custom-engine-c-http-note.md](./examples/custom-engine-c-http-note.md). |

Lista nu e exhaustivă: **orice motor** care poate face HTTPS din procesul care deține cheia (sau dintr-un backend lângă el) poate integra ZPL la fel — diferența e doar **codul de legătură** pe care îl scrii tu sau generezi.

## Unity

- **Server:** `HttpClient` sau `UnityWebRequest` pe proces headless / backend .NET.
- **Client:** doar UI + comandă către serverul tău.
- **Documentație SDK repo:** [../UNITY.md](../UNITY.md) (F1 arhitectură; F2 pachet C# = mandat separat).
- **Gap-uri vs doc canonic:** [UNITY_ENGINE_GAP.md](./UNITY_ENGINE_GAP.md).
- **Snippet server `HttpClient`:** [examples/unity-httpclient-snippet.md](./examples/unity-httpclient-snippet.md).

## Godot

- **4.x:** `HTTPRequest` din GDScript pe un nod care rulează **doar pe server** (autoritative multiplayer), sau pe un mic serviciu separat care vorbește cu Godot prin RPC.
- Evită să pui cheia în `export` Android/iOS.
- **Snippet complet + capcane export:** [examples/godot-server-snippet.md](./examples/godot-server-snippet.md).
- **Export Web (HTML5 / WASM):** fără cheie ZPL în client browser — **BFF**; vezi [examples/godot-web-export-bff-note.md](./examples/godot-web-export-bff-note.md).
- **Distribuții comerciale (ex. W4 Games):** același flux HTTP ca Godot 4; vezi [examples/w4-godot-note.md](./examples/w4-godot-note.md).

### Godot: erori HTTP, retry, `tokens_used` (G2)

- **`HTTPRequest.RESULT_*`:** dacă `result != RESULT_SUCCESS`, nu încerca să parsezi body; log + backoff.
- **Cod HTTP:** `401` cheie invalidă; `402` plan / plată; `429` rate limit — respectă `Retry-After` dacă există; fără retry agresiv pe 401/402.
- **`tokens_used`:** dacă API-ul îl returnează, poți afișa în consola serverului sau agrega în billing intern; nu expune jucătorului detalii sensibile de cont.
- **Idempotency:** pentru același batch de observații, evită dublu POST din cauza reconectărilor — folosește id de run sau debounce.

## Unreal

- **`FHttpModule`** / `IHttpRequest` din **GameMode** server sau subsystem dedicat, **nu** în client packaging.
- Blueprint-uri: cel mult apelează **endpoint propriu** C++ care face HTTPS către ZPL.
- **Sketch C++ + checklist packaging:** [examples/unreal-http-subsystem-sketch.md](./examples/unreal-http-subsystem-sketch.md).
- **Șablon Lyra (GAS, dedicated server):** [examples/unreal-lyra-packaging-note.md](./examples/unreal-lyra-packaging-note.md).

## Bevy (Rust)

- **Server / bin headless:** `reqwest` + `tokio`; cheia din env. Nu compila același bin pentru wasm client cu cheie.
- **Snippet:** [examples/bevy-reqwest-snippet.md](./examples/bevy-reqwest-snippet.md).

## Defold (Lua)

- **`http.request`** asincron; cheia în config **server-only** sau, preferat, BFF separat.
- **Snippet:** [examples/defold-http-snippet.md](./examples/defold-http-snippet.md).

## Web: TypeScript (Phaser, Pixi, Cocos Creator în browser)

- **BFF same-origin** sau API de joc: browserul nu primește cheia ZPL.
- **Snippet:** [examples/web-typescript-bff-snippet.md](./examples/web-typescript-bff-snippet.md).

## GameMaker (GML)

- **`http_request`** + evenimente async; pentru jucători folosește bridge-ul tău, nu ZPL direct.
- **Snippet:** [examples/gamemaker-gml-http-snippet.md](./examples/gamemaker-gml-http-snippet.md).

## Flame / Flutter (Dart)

- **Flame** rulează deasupra Flutter: același pattern **BFF** ca web-ul TypeScript.
- **Snippet:** [examples/flame-dart-http-snippet.md](./examples/flame-dart-http-snippet.md).

## Roblox (Luau)

- **`HttpService`** doar din **server**; URL BFF pe **allowlist** în Game Settings; fără cheie ZPL în `ServerStorage` accesibil greșit.
- **Snippet:** [examples/roblox-httpservice-snippet.md](./examples/roblox-httpservice-snippet.md).

## MonoGame / FNA (C#)

- **`HttpClient`** identic ca Unity headless; evită duplicarea — urmează snippet-ul Unity.
- **Notă scurtă:** [examples/monogame-httpclient-note.md](./examples/monogame-httpclient-note.md).

## Ren'Py

- **`renpy.fetch`** sau BFF extern; nu include cheia ZPL în build-ul distribuit jucătorilor.
- **Snippet:** [examples/renpy-http-bridge-snippet.md](./examples/renpy-http-bridge-snippet.md).

## Love2D (LÖVE)

- Preferă **BFF** / microserviciu; TLS în Lua necesită stack ales cu grijă.
- **Snippet:** [examples/love2d-bridge-snippet.md](./examples/love2d-bridge-snippet.md).

## .NET MAUI

- **`HttpClient`** + permisiuni mobile; cheia doar pe server / BFF.
- **Notă:** [examples/dotnet-maui-http-note.md](./examples/dotnet-maui-http-note.md).

## Redot

- Același flux ca **Godot 4** pentru apeluri HTTP server-side.
- **Notă:** [examples/redot-godot-note.md](./examples/redot-godot-note.md).

## Construct 3

- **AJAX** (sau echivalent) către **BFF**; configurare domenii pentru preview / export.
- **Snippet:** [examples/construct3-ajax-bff-snippet.md](./examples/construct3-ajax-bff-snippet.md).

## Haxe / OpenFL / Heaps

- **OpenFL / JS:** `haxe.Http` / `fetch` / `URLRequest` către BFF.
- **Heaps:** același BFF; pe web folosește `fetch` sau API-ul Heaps pentru HTTP (vezi versiunea ta).
- **Snippet:** [examples/haxe-openfl-http-snippet.md](./examples/haxe-openfl-http-snippet.md).

## GDevelop 5

- **Extensii rețea** sau **JS** către BFF; fără cheie ZPL în variabile exportate.
- **Snippet:** [examples/gdevelop-fetch-bff-snippet.md](./examples/gdevelop-fetch-bff-snippet.md).

## Clickteam Fusion 2.5+

- **GET/POST** sau extensii rețea către **BFF**; fără cheie în `.mfa` / exporturi mobile sau HTML5.
- **Snippet:** [examples/fusion-clickteam-bff-snippet.md](./examples/fusion-clickteam-bff-snippet.md).

## Stencyl

- **Blocuri HTTP** sau **Haxe** în modul Code către **BFF**; fără cheie în atribute exportate.
- **Snippet:** [examples/stencyl-http-bff-snippet.md](./examples/stencyl-http-bff-snippet.md).

## PICO-8

- Rețea **limitată**; ZPL serios = **BFF în afara cartușului** sau alt stack (vezi notă).
- **Notă:** [examples/pico8-limit-note.md](./examples/pico8-limit-note.md).

## Stride (C# / .NET)

- **`HttpClient`** pe proces server / serviciu .NET; clientul Stride nu deține cheia ZPL.
- **Notă:** [examples/stride-httpclient-note.md](./examples/stride-httpclient-note.md).

## Flax (C# / .NET)

- **`HttpClient`** în cod **server-only** / dedicated sau BFF .NET; build-ul client Flax nu include cheia ZPL.
- **Notă:** [examples/flax-httpclient-note.md](./examples/flax-httpclient-note.md).

## O3DE (C++)

- **Gems / componente server:** HTTP (CRT / curl / stack ales) doar pe **dedicated** / headless; vezi nota.
- **Notă:** [examples/o3de-http-cpp-note.md](./examples/o3de-http-cpp-note.md).

## CryEngine / Lumberyard (C++)

- **Dedicated server** + client HTTP în DLL server; fără cheie în `.pak` client.
- **Notă:** [examples/cryengine-http-cpp-note.md](./examples/cryengine-http-cpp-note.md).

## Source 2 (Valve)

- **Dedicated server** / proces separat de client; fără cheie în **VPK**-uri livrate jucătorilor.
- **Notă:** [examples/source2-server-http-note.md](./examples/source2-server-http-note.md).

## id Tech (id Software)

- **Dedicated server** + pachete client; fără cheie ZPL în `.pak` / config client.
- **Notă:** [examples/idtech-dedicated-server-http-note.md](./examples/idtech-dedicated-server-http-note.md).

## Serious Engine (Croteam)

- **Dedicated server** C++ (și scripturi server-side unde există); cheia ZPL rămâne în procesul server sau într-un **BFF** lângă el — nu în pachetele livrate clientului.
- **Notă:** [examples/serious-engine-http-cpp-note.md](./examples/serious-engine-http-cpp-note.md).

## Motor propriu (C / C++)

- **`libcurl`** (sau BFF + SDK) pe **worker** / daemon; clienții nu văd cheia.
- **Notă:** [examples/custom-engine-c-http-note.md](./examples/custom-engine-c-http-note.md).

## HTTP comun (Unity / Godot / Unreal)

| Cod | Semnificație tipică | Acțiune joc |
|-----|----------------------|-------------|
| 200 | OK | Parse doar câmpuri publice contractuale. |
| 401 | Neautorizat | Verifică cheia pe server; nu retry infinit. |
| 402 | Plată / plan | UX: upgrade; nu fabrica scor. |
| 429 | Rate limit | Backoff; respectă limitele planului. |
| 5xx | Indisponibil | „Data unavailable”; retry limitat. |

**Regulă:** niciodată scor AIN inventat când API-ul eșuează — același principiu ca în `zpl_nodeweb/src/lib/demo-engine.ts` (ZPL Main) pentru web.

## RNG în joc

- **RNG-ul gameplay** (loot, crit) = responsabilitatea ta; poate fi îmbunătățit independent.
- **ZPL** = strat de **măsură** pe datele agregate sau pe stream-uri pe care le definești tu în contract.

## Abonamente

- Același model ca web: **plan + tokeni** legați de cheie; motorul returnează **402/429** când e cazul. Jocul tău tratează erorile ca „serviciu indisponibil / upgrade”.

## Organizare în repo (sugestie)

- Un folder sau repo **`zpl-integration-unity`**, altul **`zpl-integration-godot`**, etc., **doar** pentru exemple și glue — fără duplicarea logicii AIN; totul apelează același API.
