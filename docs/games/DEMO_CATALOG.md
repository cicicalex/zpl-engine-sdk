# Catalog demo-uri web (ZPL Main)

## Poziționare (neutralitate ca strat de decizie)

ZPL în aceste demo-uri este **strat de decizie privind neutralitatea**: simularea din browser produce **observații** (distribuții, win rates, drift); rezultatul motorului (`ain`, `ain_status`, semnal) te ajută să **evaluezi** dacă datele par suficient de neutre / stabile pentru scenariul afișat — nu înlocuiește RNG-ul local al demo-ului. În producție legi tu politica (alertă, gate, raport).

## Unde e codul

| Rol | Path relativ din `C:\Dev` |
|-----|-----------------------------|
| Pagini demo (EN root) | `zpl_nodeweb/src/app/demos/` (proiect ZPL Main Next.js) |
| Pagini demo (`[lang]`) | `zpl_nodeweb/src/app/[lang]/demos/` |
| Client HTTP demo | `zpl_nodeweb/src/lib/demo-engine.ts` — `POST /api/compute` + header `X-ZPL-Demo` |
| Panou rezultat | `zpl_nodeweb/src/components/demos/engine-result.tsx` |
| Listă marketing | `zpl_nodeweb/src/app/demos/demos-client.tsx` (`gameDemos`) |

**URL public:** `https://zeropointlogic.io/demos/<slug>` (și variantă cu prefix limbă dacă e activată).

## Tabel: slug → cod → ce pliază în ZPL

Toate rândurile de mai jos folosesc același pattern: **simulare locală** → scor `value` în `[0,1]` (+ `runs` / `scale` opțional) → `callEngine` → câmpuri publice afișate în UI.

| Slug | Titlu (din UI) | Tag / gen | Path pagină (root) | Path pagină `[lang]` |
|------|----------------|-----------|--------------------|----------------------|
| `dice-fairness` | Dice Fairness Check | Fairness | `zpl_nodeweb/src/app/demos/dice-fairness/page.tsx` | `zpl_nodeweb/src/app/[lang]/demos/dice-fairness/page.tsx` |
| `coin-flip` | Coin Flip Bias | Fairness | `zpl_nodeweb/src/app/demos/coin-flip/page.tsx` | `zpl_nodeweb/src/app/[lang]/demos/coin-flip/page.tsx` |
| `loot-box` | Loot Box Drop Rates | Loot | `zpl_nodeweb/src/app/demos/loot-box/page.tsx` | `zpl_nodeweb/src/app/[lang]/demos/loot-box/page.tsx` |
| `gacha` | Gacha Pull Verification | Gacha | `zpl_nodeweb/src/app/demos/gacha/page.tsx` | `zpl_nodeweb/src/app/[lang]/demos/gacha/page.tsx` |
| `card-battle` | Card Battle Fairness | PvP | `zpl_nodeweb/src/app/demos/card-battle/page.tsx` | `zpl_nodeweb/src/app/[lang]/demos/card-battle/page.tsx` |
| `battle-royale` | Battle Royale Combat | PvP | `zpl_nodeweb/src/app/demos/battle-royale/page.tsx` | `zpl_nodeweb/src/app/[lang]/demos/battle-royale/page.tsx` |
| `pvp-arena` | PvP Arena Balance | PvP | `zpl_nodeweb/src/app/demos/pvp-arena/page.tsx` | `zpl_nodeweb/src/app/[lang]/demos/pvp-arena/page.tsx` |
| `racing` | Race Outcome Fairness | Racing | `zpl_nodeweb/src/app/demos/racing/page.tsx` | `zpl_nodeweb/src/app/[lang]/demos/racing/page.tsx` |
| `crafting` | Crafting RNG | Crafting | `zpl_nodeweb/src/app/demos/crafting/page.tsx` | `zpl_nodeweb/src/app/[lang]/demos/crafting/page.tsx` |
| `mmo-quest` | MMO Drop Rolls | RPG | `zpl_nodeweb/src/app/demos/mmo-quest/page.tsx` | `zpl_nodeweb/src/app/[lang]/demos/mmo-quest/page.tsx` |
| `economy` | Economy Stability | Economy | `zpl_nodeweb/src/app/demos/economy/page.tsx` | `zpl_nodeweb/src/app/[lang]/demos/economy/page.tsx` |
| `slots` | Slot Machine RNG | Casino | `zpl_nodeweb/src/app/demos/slots/page.tsx` | `zpl_nodeweb/src/app/[lang]/demos/slots/page.tsx` |
| `matchmaking` | Matchmaking Balance | Multiplayer | `zpl_nodeweb/src/app/demos/matchmaking/page.tsx` | `zpl_nodeweb/src/app/[lang]/demos/matchmaking/page.tsx` |
| `rng-validator` | Custom RNG Validator | Security | `zpl_nodeweb/src/app/demos/rng-validator/page.tsx` | `zpl_nodeweb/src/app/[lang]/demos/rng-validator/page.tsx` |

### Hub meta (nu același tip ca un singur joc)

| Slug | Rol | Path |
|------|-----|------|
| `zpl-master` | Demo mare „bring your own data” + output-uri didactice | `zpl_nodeweb/src/app/demos/zpl-master/page.tsx`, `zpl_nodeweb/src/app/[lang]/demos/zpl-master/page.tsx` |

### Index listă

- `zpl_nodeweb/src/app/demos/page.tsx` — listă + metadata „14 demos”.
- `zpl_nodeweb/src/app/[lang]/demos/page.tsx` — variantă localizată.

## În afara acestui catalog

În `demos-client.tsx` mai există intrări **externe** (heatmap Finance, Zenodo, `/docs`) — nu sunt rute `demos/<slug>` locale; nu le duplicăm aici ca rânduri de cod.

## Legături

- [WEB_DEMOS.md](./WEB_DEMOS.md)
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [DEV_GAME_MODELS.md](./DEV_GAME_MODELS.md) — prototipuri tale în dev
