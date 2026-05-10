# Unreal Engine — sketch subsistem C++ + `FHttpModule`

Scop: **E1** — inițiere request pe **server**; **E2** — Blueprint doar spre endpoint propriu; cheia ZPL **nu** în pachetul client.

## 1. Subsistem de joc (server)

```cpp
// ZplComputeSubsystem.h
#pragma once
#include "Subsystems/GameInstanceSubsystem.h"
#include "ZplComputeSubsystem.generated.h"

UCLASS()
class YOURGAME_API UZplComputeSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    void RequestCompute(const FString& JsonBody);

private:
    void OnResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bSucceeded);
};
```

```cpp
// ZplComputeSubsystem.cpp
#include "ZplComputeSubsystem.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"

void UZplComputeSubsystem::RequestCompute(const FString& JsonBody)
{
    if (!GetWorld() || GetWorld()->GetNetMode() == NM_Client) // nu apela ZPL din pure client build
    {
        return;
    }

    const auto Http = &FHttpModule::Get();
    const auto Req = Http->CreateRequest();
    Req->SetURL(TEXT("https://engine.zeropointlogic.io/compute")); // sau proxy
    Req->SetVerb(TEXT("POST"));
    Req->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    // Req->SetHeader(TEXT("Authorization"), FString::Printf(TEXT("Bearer %s"), *ApiKeyFromEnv()));
    // Req->SetHeader(TEXT("X-ZPL-Client"), TEXT("your-channel"));
    Req->SetContentAsString(JsonBody);
    Req->OnProcessRequestComplete().BindUObject(this, &UZplComputeSubsystem::OnResponse);
    Req->ProcessRequest();
}

void UZplComputeSubsystem::OnResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bSucceeded)
{
    if (!bSucceeded || !Response.IsValid())
        return;
    const int32 Code = Response->GetResponseCode();
    // 200: parse JSON public fields only; 402/429: surface upgrade / cooldown; else: unavailable
}
```

**Important:** pentru **PIE** ca client, acest guard oprește request-ul (comportament dorit). Teste locale cu ZPL = rulează **dedicated listen** cu cheie în env sau folosește proxy de dev.

## 2. Blueprint boundary (E2)

- Blueprint apelează **`UKismetSystemLibrary`** → C++ `UFUNCTION(BlueprintCallable)` care trimite JSON la **URL-ul serverului tău** (nu direct ZPL), sau la subsistemul de mai sus **doar** pe instanța dedicată.
- **Packaging:** client build exclude modulele care conțin string-ul de cheie sau link direct la ZPL cu auth; varianta curată = **GameLift / custom server** deține secretul.

## 3. Checklist înainte de ship (E2)

| Verificare | Da / Nu |
|------------|---------|
| Client retail nu conține `ZPL_API_KEY` sau bearer static | |
| `DefaultEngine.ini` / `Crypto` nu leak-uiesc chei în log | |
| TLS verificat (fără `VERIFY_NONE` în producție) | |
| 402/429 mapate la UX (upgrade plan, retry-after) | |
| Doar câmpuri API publice propagate către UI client | |

## Legături

- [INTEGRATIONS_UNITY_GODOT_UNREAL.md](../INTEGRATIONS_UNITY_GODOT_UNREAL.md)
