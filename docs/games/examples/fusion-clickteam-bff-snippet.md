# Clickteam Fusion 2.5+ — HTTP / extensii către **BFF**

Scop: în **Fusion**, apelurile HTTPS se fac de obicei prin obiecte de tip **GET** / **POST** (numele exact depind de versiunea și extensiile instalate) sau prin **extensii** comunitare pentru rețea. **Cheia ZPL** nu intră în **`.mfa`** / variabile globale exportate în **HTML5**, **Android** sau **UWP**.

## Pattern recomandat

1. **Eveniment:** la momentul potrivit (sfârșit de nivel, buton debug, etc.) trimite **POST JSON** către `https://api.example.com/fusion-zpl` (BFF-ul tău).
2. **Răspuns:** parsează doar câmpuri publice; la eroare rețea sau HTTP ≠ succes, **nu** inventa `ain` (vezi [INTEGRATIONS_UNITY_GODOT_UNREAL.md](../INTEGRATIONS_UNITY_GODOT_UNREAL.md#http-comun-unity--godot--unreal)).

## Aliniere cu Construct / GDevelop

- **Export browser:** aceleași probleme **CORS** și **Origin** ca în [construct3-ajax-bff-snippet.md](./construct3-ajax-bff-snippet.md) / [gdevelop-fetch-bff-snippet.md](./gdevelop-fetch-bff-snippet.md) — BFF-ul trebuie să accepte domeniul unde rulează jocul.
- **Mobile:** fără cheie în pachet; token de sesiune de la serverul tău dacă e nevoie de autentificare joc↔BFF.

## Capcane

- **String global „ZPL_KEY”** în Fusion: vizibil în reverse engineering; folosește doar BFF.
- **Versiuni vechi fără TLS modern:** preferă BFF pe infrastructură cu TLS actualizat, nu legături nesecurizate.

OpenAPI: [openapi.yaml](../../openapi.yaml).
