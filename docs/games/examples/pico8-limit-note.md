# PICO-8 — limitări rețea și ZPL

**PICO-8** nu oferă un client HTTPS generic, stabil, către API-uri arbitrare ca un motor desktop sau un browser cu `fetch`. Cartușele sunt mici, iar modelul oficial de rețea e **limitat** (ex. BBS / scenarii specifice).

## Recomandare practică

- **Nu** încerca să îngropi cheia ZPL într-un cart `.p8.png` distribuit.
- Dacă ai nevoie de ZPL în jurul unui prototip PICO-8: folosește o **pagină web** sau un **serviciu** lângă joc care implementează BFF-ul (vezi [web-typescript-bff-snippet.md](./web-typescript-bff-snippet.md)), iar cartușul comunică doar cu acel mediu dacă rețeaua ta o permite end-to-end (de obicei **nu** direct din PICO-8 către ZPL în producție).

Pentru măsurători serioase în pipeline-ul tău de joc, preferă un motor sau un client cu **HTTPS clar** către BFF.
