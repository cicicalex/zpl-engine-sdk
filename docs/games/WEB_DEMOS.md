# Demo-uri web (`zeropointlogic.io/demos`)

**Catalog complet (slug-uri, path-uri, rol ZPL):** [DEMO_CATALOG.md](./DEMO_CATALOG.md).

## Unde e codul

- Proiect: **`C:\Dev\zpl_nodeweb`**
- Rute tipice: `src/app/demos/<nume>/page.tsx`, index `src/app/demos/page.tsx`
- Client demo comun: `src/lib/demo-engine.ts` (apel `POST /api/compute` cu `X-ZPL-Demo`)
- Panou rezultat: `src/components/demos/engine-result.tsx` (doar câmpuri publice AIN / signal / status)

## Rolul demo-urilor

- **Educație + marketing:** arată cum observațiile din joc se transformă în input pentru motor și ce răspunde API-ul.
- **RNG / simulări în browser** sunt **ilustrative** (generare date), **nu** înlocuitor al motorului.

## `zpl-master`

- Demo mare, conversion din HTML; conține **logică didactică locală** + apeluri API — mentenanță mai ușoară dacă e împărțit în module (viitor refactor, cu mandat blueprint).

## Pagini noi pe site

- Conform politicii workspace (`AGENTS.md` în monorepo-ul ZPL complet): **fără** rute noi fără plan în `SITE_BLUEPRINT_ZPL_MAIN.md`. Îmbunătățiri pe rute existente = OK cu mandat.
