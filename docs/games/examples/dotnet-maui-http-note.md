# .NET MAUI — `HttpClient` ca Unity / MonoGame

**MAUI** folosește **.NET** și **`System.Net.Http.HttpClient`** cu același model ca **Unity headless** sau **MonoGame**.

- Urmează [unity-httpclient-snippet.md](./unity-httpclient-snippet.md) pentru structura `PostAsync`, parsare JSON și coduri `401/402/429`.
- Vezi și [monogame-httpclient-note.md](./monogame-httpclient-note.md) (aceeași familie .NET).

## Specific MAUI

- **Android / iOS:** declară permisiuni de rețea și (dacă e cazul) **ATS / cleartext** doar pentru dev; în producție doar HTTPS către BFF-ul tău.
- **Windows / macOS:** fără cheie ZPL în `appsettings.json` livrat jucătorilor — folosește **secret store** sau variabile de mediu la build intern, sau exclusiv **BFF**.

Cheia ZPL rămâne pe **serverul tău** sau în **BFF**, nu în pachetul store descărcat de utilizatori.
