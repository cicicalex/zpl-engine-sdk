# ZPL Engine Python SDK — Quick Start Guide

Get up and running with the ZPL Engine SDK in minutes.

## Installation

```bash
pip install zeropointlogic
```

## Get Your API Key

1. Visit https://zeropointlogic.io/dashboard
2. Navigate to API Keys section
3. Create new key (format: `zpl_s_xxx`)
4. Copy and save securely

## Your First Request

```python
from zeropointlogic import ZPLClient

# Initialize client
client = ZPLClient(api_key="zpl_s_your_key_here")

# Create a binary matrix (0s and 1s only)
matrix = [
    [0, 1, 0, 1],
    [1, 0, 1, 0],
    [0, 1, 1, 0],
    [1, 0, 0, 1]
]

# Compute AI Neutrality Index
result = client.compute(matrix=matrix, samples=1000)

# Display results
print(f"AIN Score: {result.ain:.3f}")
print(f"Status: {result.status}")
print(f"Neutral? {result.is_neutral()}")
print(f"Tokens remaining: {result.tokens_remaining}")
```

Expected output:
```
AIN Score: 0.735
Status: STABLE
Neutral? True
Tokens remaining: 99
```

## Convert Data to Matrix

### From Price Series
```python
from zeropointlogic import matrix_from_prices

prices = [100, 105, 102, 110, 108, 115, 112]
matrix = matrix_from_prices(prices, window=3)

result = client.compute(matrix=matrix, samples=500)
print(f"Price distribution bias: {result.ain:.3f}")
```

### From Time Series
```python
from zeropointlogic import matrix_from_timeseries

values = [1.2, 3.4, 2.1, 4.5, 3.2, 5.1, 4.2]
matrix = matrix_from_timeseries(values, bins=3, method="quantile")

result = client.compute(matrix=matrix, samples=500)
```

### From Pandas DataFrame
```python
import pandas as pd
from zeropointlogic import matrix_from_dataframe

df = pd.DataFrame({
    "price": [100, 105, 102, 110],
    "volume": [1000, 1500, 1200, 1800]
})

matrix = matrix_from_dataframe(df, "price", "volume")
result = client.compute(matrix=matrix, samples=500)
```

## Monitor API Usage

```python
from zeropointlogic import ZPLClient

client = ZPLClient(api_key="zpl_s_xxx")

# Check usage
usage = client.get_usage()
print(f"Plan: {usage.plan}")
print(f"Usage: {usage.usage_percent:.1f}%")
print(f"Tokens left: {usage.tokens_remaining}")

# View all plans
plans = client.get_plans()
for plan in plans:
    print(f"{plan.name}: €{plan.price_eur:.2f}/mo")

# Check engine health
health = client.get_health()
print(f"Status: {health.status}")
print(f"Uptime: {health.uptime_percent:.2f}%")
```

## Error Handling

```python
from zeropointlogic import ZPLClient, ZPLAuthError, ZPLQuotaError

client = ZPLClient(api_key="zpl_s_xxx")

try:
    result = client.compute(matrix=[[0, 1], [1, 0]], samples=1000)
except ZPLAuthError:
    print("Invalid API key")
except ZPLQuotaError as e:
    print(f"Quota exceeded. {e.tokens_remaining} tokens left")
except Exception as e:
    print(f"Error: {e}")
```

## Async Usage

```python
import asyncio
from zeropointlogic import AsyncZPLClient

async def main():
    async with AsyncZPLClient(api_key="zpl_s_xxx") as client:
        result = await client.compute(
            matrix=[[0, 1], [1, 0]],
            samples=1000
        )
        print(f"AIN: {result.ain:.3f}")

asyncio.run(main())
```

## Real-World Examples

### Cryptocurrency Analysis
```python
from zeropointlogic import ZPLClient, matrix_from_prices

client = ZPLClient(api_key="zpl_s_xxx")

# Simulate BTC prices (in production, fetch from API)
prices = [45000, 45500, 44800, 46200, 45900, 47100]
matrix = matrix_from_prices(prices, window=3)

result = client.compute(matrix=matrix, samples=1000)
print(f"BTC bias: {result.ain:.3f} - {result.status}")
```

### Game Economy
```python
from zeropointlogic import ZPLClient, normalize_matrix

client = ZPLClient(api_key="zpl_s_xxx")

# Item rarity scores
items = [10, 85, 45, 92, 28, 73, 15, 88, 50, 30]
median = sorted(items)[len(items)//2]
matrix = [[1 if item >= median else 0 for item in items[:5]]]
matrix += [[1 if item >= median else 0 for item in items[5:]]]

result = client.compute(matrix=matrix, samples=500)
print(f"Item balance: {result.ain:.3f}")
if result.is_neutral(threshold=0.65):
    print("✓ Balanced economy")
else:
    print("⚠ Needs rebalancing")
```

## API Plans

| Plan | Tokens/Month | Cost |
|------|--------------|------|
| Free | 100 | Free |
| Basic | 10,000 | €9/mo |
| Pro | 50,000 | €27/mo |
| GamePro | 150,000 | €63/mo |
| Studio | 500,000 | €137/mo |
| Agent | 2,000,000 | €183/mo |
| Enterprise | 10,000,000 | €459/mo |
| XL | Unlimited | €919/mo |

## Status Values

- `CERTIFIED_NEUTRAL` — Perfect distribution (ain >= 0.85)
- `STABLE` — High neutrality (ain >= 0.70)
- `MODERATE_BIAS` — Some bias detected (ain >= 0.55)
- `HIGH_BIAS` — Significant bias (ain >= 0.40)
- `CRITICAL_BIAS` — Extreme bias (ain < 0.25)

## Useful Methods

```python
# ComputeResult
result.is_neutral(threshold=0.7)  # Check if AIN >= threshold
result.is_stable()                 # Check if status is neutral/stable
result.has_bias()                  # Check if status contains BIAS

# UsageInfo
usage.usage_percent                # Get usage as percentage (0-100)
usage.is_unlimited                 # Check if plan is unlimited

# PlanInfo
plan.is_free()                     # Check if free tier

# HealthStatus
health.is_healthy()                # Check if up and >99% uptime
```

## Environment Variables

```bash
export ZPL_API_KEY="zpl_s_your_key_here"
```

Then use in code:
```python
import os
api_key = os.getenv("ZPL_API_KEY")
client = ZPLClient(api_key=api_key)
```

## Common Issues

### "Invalid API key"
- Check your API key format (should start with `zpl_s_`)
- Verify it hasn't been rotated/revoked
- Ensure no whitespace around the key

### "Quota exceeded"
- Check `usage.tokens_remaining`
- Upgrade your plan
- Reduce `samples` parameter (lower = fewer tokens)

### "Connection timeout"
- Check internet connection
- Increase timeout: `ZPLClient(api_key="...", timeout=60)`
- Retry (SDK has built-in exponential backoff)

## Next Steps

1. Read the full README: `/sessions/gifted-sharp-ritchie/mnt/Dev/Proiecte/zpl-python-sdk/README.md`
2. Explore examples: `examples/crypto_bias.py`, `examples/game_economy.py`
3. Run tests: `pytest tests/`
4. Check API status: `client.get_health()`

## Support

- **Docs**: https://github.com/zeropointlogic/zpl-python-sdk
- **Issues**: https://github.com/zeropointlogic/zpl-python-sdk/issues
- **Email**: support@zeropointlogic.io

Happy analyzing!
