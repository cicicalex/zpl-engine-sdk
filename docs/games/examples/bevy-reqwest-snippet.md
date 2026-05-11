# Bevy (Rust) — apel ZPL cu `reqwest` (proces server)

Scop: **ECS / headless** sau bin dedicat (nu player-ul descărcat de jucători) face HTTPS către ZPL. Cheia API vine din **env** sau secret manager, compilată fără literal în artefactul public.

## De ce nu „în Bevy client”

- Build-ul jucătorului nu trebuie să conțină `ZPL_API_KEY`. Fie **server dedicat** Bevy + `reqwest`, fie **microserviciu** Rust lângă Bevy care primește observații prin gRPC/UDP și apelează ZPL (vezi [SDK_VS_HTTP.md](../SDK_VS_HTTP.md)).

## Dependențe tipice (Cargo)

- `reqwest` cu feature `json` + `rustls-tls` (sau stack-ul TLS ales de echipă).
- `tokio` cu `rt-multi-thread`, `macros` — pentru `async` în bin server.
- `serde`, `serde_json` pentru corpul `POST /compute` (aliniat la [openapi.yaml](../../openapi.yaml) după sync / în monorepo).

## Schiță: `tokio::main` + POST

```rust
// bin server-only — NU în wasm client
use reqwest::header::{AUTHORIZATION, CONTENT_TYPE, HeaderMap, HeaderValue};
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let key = std::env::var("ZPL_API_KEY").expect("ZPL_API_KEY set only on server");
    let url = std::env::var("ZPL_COMPUTE_URL")
        .unwrap_or_else(|_| "https://engine.zeropointlogic.io/compute".into());

    let client = reqwest::Client::builder().build()?;
    let body = json!({
        "value": 0.52,
        "runs": 2000,
        "scale": 8
    });

    let mut headers = HeaderMap::new();
    headers.insert(CONTENT_TYPE, HeaderValue::from_static("application/json"));
    headers.insert(
        AUTHORIZATION,
        HeaderValue::from_str(&format!("Bearer {}", key))?,
    );

    let res = client.post(&url).headers(headers).json(&body).send().await?;
    let status = res.status();
    let text = res.text().await?;
    if !status.is_success() {
        eprintln!("ZPL HTTP {}: {}", status, text);
        return Ok(());
    }
    // Parse doar câmpuri publice contractuale (ain, ain_status, etc.) — fără a expune cheia în log.
    println!("{}", text);
    Ok(())
}
```

## Capcane

- **`unwrap` pe cheie în client wasm:** compile-time / CI trebuie să excludă acest bin din target-uri wasm.
- **429 / 401 / 402:** același tabel ca în [INTEGRATIONS_UNITY_GODOT_UNREAL.md](../INTEGRATIONS_UNITY_GODOT_UNREAL.md#http-comun-unity-godot-unreal); backoff pe 429.
- **Blocking în sistem Bevy:** dacă apelezi din `System`, preferă **task** Tokio detașat sau canal către thread dedicat ca să nu blochezi scheduler-ul Bevy pe frame.

Documentație canonică arhitectură (F1 Unity, același API): [UNITY.md](../../UNITY.md).
