# Roblox — `HttpService` către **BFF-ul tău** (fără cheie ZPL în joc)

Scop: în Roblox **nu** pune cheia API ZPL în `ServerScriptService` dacă acel cod sau datele sensibile pot ajunge în telemetrie greșită sau în copii de place. Modelul sigur: **doar URL-ul BFF-ului tău** e apelat din joc; cheia ZPL rămâne pe infrastructura ta (VPS, Cloudflare Worker, etc.).

## Cerințe Roblox

- **`HttpService.HttpEnabled = true`** în Studio + domeniul BFF adăugat în **Game Settings → Security → Allow HTTP requests** (allowlist explicită).
- Apeluri din **`Script` / `ModuleScript` server-only** (sub `ServerScriptService`), nu din `LocalScript` pentru logica ZPL.

## Schiță Luau (server) cu `RequestAsync`

```lua
-- ServerScriptService/ZplBridge.server.lua
local HttpService = game:GetService("HttpService")

local BFF_URL = "https://api.example.com/roblox-zpl" -- pe allowlist în Game Settings

local function postObservations(payload)
	local ok, response = pcall(function()
		return HttpService:RequestAsync({
			Url = BFF_URL,
			Method = "POST",
			Headers = {
				["Content-Type"] = "application/json",
				-- Opțional: secret joc↔BFF (HMAC); NU cheia ZPL.
				["X-Roblox-Secret"] = "…",
			},
			Body = HttpService:JSONEncode(payload),
		})
	end)
	if not ok or not response.Success then
		return nil
	end
	return response.StatusCode, response.Body
end
```

Tratează `401/402/429` ca în tabelul comun din [INTEGRATIONS_UNITY_GODOT_UNREAL.md](../INTEGRATIONS_UNITY_GODOT_UNREAL.md#http-comun-unity--godot--unreal).

## Capcane

- **Cheia ZPL în `StringValue` / DataStore:** orice acces greșit o expune; evită complet.
- **Client replication:** nimic legat de ZPL în `ReplicatedStorage` pentru jucători.
- **Rate limits Roblox:** throttle intern + respectă răspunsurile `429` de la BFF/ZPL.

OpenAPI: [openapi.yaml](../../openapi.yaml).
