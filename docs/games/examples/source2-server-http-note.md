# Source 2 (Valve) — HTTPS din **dedicated server**, nu din client

Pe **Source 2** (și familia **Source** clasică), logica de gameplay pe **dedicated server** rulează într-un proces separat de clienții care descarcă conținutul (ex. **VPK**). Integrarea ZPL trebuie să trăiască acolo sau într-un **serviciu lateral** care primește date de la server prin canalul tău deja existent.

## Recomandări

- **Cheia ZPL** în **variabile de mediu** / secret store pe mașina **SRCDS** (sau echivalent), nu în fișiere din pachetele livrate clienților.
- **Client HTTP:** folosește biblioteca suportată de stack-ul tău pe **Linux/Windows server** (ex. **libcurl**, WinHTTP) din codul încărcat **doar** pe target **dedicated server** — nu din DLL-uri partajate 1:1 cu clientul dacă asta expune simboluri sau date.
- **Rețea Steam / GNS:** ZPL rămâne **HTTPS la engine** sau la **BFF**; socket-urile tale duc **observații** și **rezultate derivate**, nu cheia către clienți.

## Referință conceptuală

- Checklist server C++ (async, fără cheie în pachet client): [unreal-http-subsystem-sketch.md](./unreal-http-subsystem-sketch.md) — principii aplicabile; API-ul concret e al proiectului tău Source 2.

OpenAPI: [openapi.yaml](../../openapi.yaml).
