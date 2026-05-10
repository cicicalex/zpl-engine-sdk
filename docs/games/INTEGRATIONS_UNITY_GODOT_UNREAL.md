# Motoare de joc — integrare ZPL (Unity, Godot, Unreal și altele)

## Un contract, mai multe „scrieri”

- **ZPL Engine** expune același **API HTTP** (JSON) indiferent de motor.
- **Fiecare motor** are propriul runtime, limbaj și uneori threading: integrarea nu e un singur fișier universal, ci **câte un strat de glue** (sau repo mic) per motor — Unity (C#), Godot (GDScript/C#), Unreal (C++), plus altele mai jos.
- **SDK-urile oficiale** TypeScript/Python sunt pentru **Node/Python**, nu „magia” care rulează în interiorul editorului Unity/Godot; acolo folosești **HTTP nativ** sau un client **generat din OpenAPI** / viitor pachet C# dedicat.

## Regulă de aur: **server authoritative**

- **Cheia API** (`zpl_u_…`) stă pe **backend-ul** tău (dedicated server, Cloud Run, PlayFab Cloud Script, etc.), **nu** în build-ul clientului descărcat de jucători.
- Clientul jocului primește doar **rezultatul derivat** (ex. verdict, tier, cooldown) pe canalul tău deja securizat (WebSocket, HTTPS la serverul de joc).

## Matrice: motor → unde scrii apelul ZPL

| Motor / platformă | Limbaje tipice pe server | Client HTTP obișnuit | Notă |
|-------------------|--------------------------|----------------------|------|
| **Unity** | C# (.NET / IL2CPP headless) | `HttpClient`, `UnityWebRequest` | Glue separat de Godot/Unreal. |
| **Godot** | GDScript, C# | `HTTPRequest`, uneori `HTTPClient` (C#) | Nod sau autoload **doar pe server** în multiplayer autoritar. |
| **Unreal** | C++ | `FHttpModule` / `IHttpRequest` | Subsystem sau GameMode **server**; Blueprint → endpoint propriu C++. |
| **Bevy** (Rust) | Rust | `reqwest`, `ureq` | Server ECS sau bin separat care apelează ZPL. |
| **Defold** | Lua | `http.request` | Din context server / serviciu extern cu cheia. |
| **GameMaker** | GML | `http_request` | Preferă job server sau extensie care nu expune cheia în client. |
| **Cocos** (Creator / etc.) | TypeScript / C++ / Lua | `fetch`, `XMLHttpRequest`, native HTTP | Poate folosi același pattern ca web BFF dacă ești în TS. |
| **MonoGame / FNA** | C# | `HttpClient` | La fel ca Unity din punct de vedere HTTP. |
| **Ren'Py** | Python | `requests`, `urllib` | Cheia tot pe server; nu în distributiv vizibil jucătorului. |
| **Love2D** | Lua | `https` (luasec) sau serviciu separat | Adesea mai simplu: microserviciu Node/Python cu SDK. |
| **Phaser / Pixi / Vite** | TypeScript | `fetch` către **BFF** | Cheia doar pe server; vezi snippet web. |

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

### Godot: erori HTTP, retry, `tokens_used` (G2)

- **`HTTPRequest.RESULT_*`:** dacă `result != RESULT_SUCCESS`, nu încerca să parsezi body; log + backoff.
- **Cod HTTP:** `401` cheie invalidă; `402` plan / plată; `429` rate limit — respectă `Retry-After` dacă există; fără retry agresiv pe 401/402.
- **`tokens_used`:** dacă API-ul îl returnează, poți afișa în consola serverului sau agrega în billing intern; nu expune jucătorului detalii sensibile de cont.
- **Idempotency:** pentru același batch de observații, evită dublu POST din cauza reconectărilor — folosește id de run sau debounce.

## Unreal

- **`FHttpModule`** / `IHttpRequest` din **GameMode** server sau subsystem dedicat, **nu** în client packaging.
- Blueprint-uri: cel mult apelează **endpoint propriu** C++ care face HTTPS către ZPL.
- **Sketch C++ + checklist packaging:** [examples/unreal-http-subsystem-sketch.md](./examples/unreal-http-subsystem-sketch.md).

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
