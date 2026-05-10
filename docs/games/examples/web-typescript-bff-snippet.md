# Web (TypeScript) — Phaser, Pixi, Vite: BFF către ZPL

Scop: **browserul jucătorului nu vede niciodată cheia ZPL**. Pagina sau jocul (Phaser, PixiJS, Three, vanilla) trimite observații la **același origin** sau la **serverul tău de joc**; acel server face `fetch`/`POST` către ZPL cu `Authorization`.

## Flux

```
Browser (TS)  --HTTPS-->  BFF same-origin / game API  --HTTPS-->  engine.zeropointlogic.io/compute
        fără cheie ZPL              cheia ZPL doar aici
```

Același principiu ca demo-urile din `zpl_nodeweb` (vezi [WEB_DEMOS.md](../WEB_DEMOS.md)): contract JSON clar, fără scor inventat când API-ul eșuează.

## BFF minimal (Node / Next route handler)

```typescript
// Route server-only — variabile din env Coolify / Vercel / etc.
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const body = await req.json();
  const key = process.env.ZPL_API_KEY;
  if (!key) return NextResponse.json({ error: "Server misconfigured" }, { status: 500 });

  const upstream = await fetch("https://engine.zeropointlogic.io/compute", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${key}`,
    },
    body: JSON.stringify(body),
  });

  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
```

## Client Phaser / Vite (fără cheie)

```typescript
const r = await fetch("/api/zpl-proxy", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ value: 0.5, runs: 2000, scale: 8 }),
});
if (!r.ok) {
  // UX: „Analiză indisponibilă” — nu fabrica AIN.
  return;
}
const data = await r.json();
```

## Cocos Creator (TypeScript)

- **Aceeași scriere:** scripturi „server” sau build HTML5 care lovesc **doar** BFF-ul tău; Creator 3.x `fetch` identic cu exemplul de mai sus când rulezi în browser.

## Coduri HTTP

- Vezi tabelul comun în [INTEGRATIONS_UNITY_GODOT_UNREAL.md](../INTEGRATIONS_UNITY_GODOT_UNREAL.md#http-comun-unity--godot--unreal).
