# Defold — `http.request` către ZPL (Lua, server / serviciu)

Scop: **Lua** dintr-un context unde **nu** expui cheia în `game.project` pentru build-uri client. Variante: **extensie server**, **cloud function**, sau **HTTP către propriul BFF**; clientul Defold vorbește doar cu serverul tău.

## Pattern recomandat

1. **Propriul endpoint** (Node, Rust, etc.) primește observații de la clientul Defold (fără cheie ZPL).
2. Backend-ul face `POST` către ZPL cu `Authorization: Bearer …`.

Dacă totuși apelezi ZPL direct dintr-un **headless** Defold / tool intern:

```lua
-- Rulează DOAR în mediu server / CI; nu împacheta cheia în bundle public.
local ZPL_URL = "https://engine.zeropointlogic.io/compute"
local key = sys.get_config("zpl.api_key") -- setat doar pe server din env / game.project server-only

local headers = {
    ["Content-Type"] = "application/json",
    ["Authorization"] = "Bearer " .. key,
}

local body = json.encode({
    value = 0.5,
    runs = 1000,
    scale = 8
})

http.request(ZPL_URL, "POST", http_response, headers, body)

function http_response(self, id, response)
    if response.status ~= 200 then
        print("ZPL error", response.status, response.body)
        return
    end
    local data = json.decode(response.body)
    -- Folosește doar câmpuri publice (ain, ain_status, …).
end
```

## Capcane Defold

- **`game.project` în repo:** nu comite valori pentru `zpl.api_key`; folosește override local sau variabile de mediu la build server.
- **Coroutines vs `http.request`:** răspunsul e asincron; nu bloca logica gameplay pe thread-ul principal fără coadă sau state machine.
- **TLS:** pe mobile verifică lanțul de certificate (Defold folosește platform defaults).

OpenAPI: [openapi.yaml](../../openapi.yaml).
