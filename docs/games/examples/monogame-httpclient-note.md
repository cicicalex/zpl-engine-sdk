# MonoGame / FNA — același model ca Unity (`HttpClient`)

**MonoGame** și **FNA** folosesc **.NET** și **`System.Net.Http.HttpClient`** (sau `HttpClientHandler`) la fel ca un server Unity headless sau un serviciu console C#.

- **Nu** duplica documentația: urmează [unity-httpclient-snippet.md](./unity-httpclient-snippet.md) (încărcare cheie din env, `PostAsync`, parsare JSON, coduri `401/402/429`).
- **Fereastra de joc vs proces headless:** dacă vrei ZPL din gameplay, tot **server authoritative** sau **BFF**; build-ul distribuit jucătorilor nu conține cheia.

Gap-uri Unity vs runtime MonoGame (export, IL2CPP): tratează-le ca orice alt proiect .NET — principiul HTTP rămâne identic.
