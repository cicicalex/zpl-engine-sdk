# Unity — `HttpClient` pe server (snippet)

Aliniat cu **F1** din [UNITY.md](../../UNITY.md): cheia rămâne pe procesul server, nu în player build.

## C# minimal (headless / backend)

```csharp
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

// Rulează doar în assembly-ul serverului sau în #if DEDICATED_SERVER
public sealed class ZplComputeClient : IDisposable
{
    private readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(30) };
    private readonly string _apiKey; // din env, Secret Manager, etc.

    public ZplComputeClient(string apiKey, string? baseUrl = null)
    {
        _apiKey = apiKey;
        _http.BaseAddress = new Uri(baseUrl ?? "https://engine.zeropointlogic.io/");
        _http.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", _apiKey);
        // _http.DefaultRequestHeaders.Add("X-ZPL-Client", "your-channel");
        // _http.DefaultRequestHeaders.Add("X-ZPL-Client-Version", "1.0.0");
    }

    public async Task<JsonElement?> PostComputeAsync(object body, CancellationToken ct = default)
    {
        var json = JsonSerializer.Serialize(body);
        using var content = new StringContent(json, Encoding.UTF8, "application/json");
        var resp = await _http.PostAsync("compute", content, ct).ConfigureAwait(false);
        if (!resp.IsSuccessStatusCode)
            return null; // UI: "Data unavailable" — fără scor inventat
        var text = await resp.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
        using var doc = JsonDocument.Parse(text);
        return doc.RootElement.Clone();
    }

    public void Dispose() => _http.Dispose();
}
```

## Note

- **Player build:** nu referi `ZplComputeClient` din cod care se compilează în client; folosește **asmdef** separate sau simbol `DEDICATED_SERVER`.
- **Retry:** exponential backoff pentru 429/503; nu pentru 401/402 (plan / cheie).
- Detalii arhitectură: [UNITY.md](../../UNITY.md), gap-uri vs doc: [UNITY_ENGINE_GAP.md](../UNITY_ENGINE_GAP.md).
