# Unreal — șablon **Lyra** și apeluri ZPL (dedicated server)

**Lyra** este un starter GAS-heavy; pentru ZPL nu se schimbă regula: **`FHttpModule` / `IHttpRequest` pe proces dedicat server**, cheia în **env / secret manager** pe mașina sau containerul care rulează **server build**, nu în clientul descărcat de jucători.

## Ce să reții

- **Target build:** folosește **Dedicated Server** (sau echivalent) pentru codul care poartă cheia sau apelează BFF-ul intern; **client** = UI + replicare.
- **GameFeaturePlugins / module:** mută logica HTTP ZPL într-un modul încărcat **doar** pe server sau în ramuri `#if WITH_SERVER_CODE` dacă împărți sursa (vezi și politica echipei pentru `#if` — ideea e să nu linkezi secrete în target client).
- **Blueprint:** la fel ca în sketch-ul general — cel mult un endpoint C++ propriu care face HTTPS; vezi [unreal-http-subsystem-sketch.md](./unreal-http-subsystem-sketch.md).

## Lyra + multiplayer

- Dacă folosești **listen server** în dev, tratează apelurile ZPL ca **autoritative** doar când `GetNetMode() == NM_DedicatedServer` (sau echivalentul configurat în proiect), ca să nu copiezi accidental obiceiul de a rula HTTP din client.

OpenAPI: [openapi.yaml](../../openapi.yaml).
