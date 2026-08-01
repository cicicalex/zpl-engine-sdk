# ZPL Engine Python SDK

Professional Python client library for the **Zero Point Logic (ZPL) Engine API** — a mathematical platform for AI Neutrality Index (AIN) analysis and stability calculations.

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Sync and Async clients** — Both `ZPLClient` (requests) and `AsyncZPLClient` (httpx) for maximum flexibility
- **AI Neutrality Index (AIN)** — Analyze bias and stability in any binary matrix data
- **Comprehensive error handling** — Specialized exceptions for auth, quota, rate limits, validation
- **Retry logic** — Exponential backoff for resilient network requests
- **Type hints** — Full type safety with Python 3.9+ compatibility
- **Production-grade** — Structure and quality comparable to OpenAI Python SDK
- **Rich utilities** — Matrix conversion from prices, timeseries, pandas DataFrames
- **Detailed documentation** — Docstrings, examples, and type information throughout

## v2.0.0 — BREAKING + REQUIRED UPGRADE

v1.x sent `{matrix, samples}` to the engine, which the Rust API rejected
with `400 Failed to deserialize: missing field 'bias'`. Every single v1.x
call failed on the wire. v2.0.0 fixes the body shape and is the first
working release.

**Upgrade immediately:** `pip install -U zeropointlogic`

Public API surface (`client.compute(matrix=..., samples=...)`) is unchanged.
Under the hood the SDK now derives `d = len(matrix)` and `bias = sum_of_1s
/ (d * d)` client-side, then posts `{d, bias, samples}` to the engine.

## Step 1 — Get an API key (DO THIS FIRST)

This SDK is a thin HTTP client. It does NOT log you in, register an
account, or mint a key for you. Calling `client.compute(...)` without a
valid `zpl_u_…` user key returns `401 Unauthorized` immediately.

You must obtain a key first, by ONE of these three paths:

### 1. Dashboard (recommended for server / app use)

1. Visit **<https://zeropointlogic.io/auth/register>** and create an
   account. Free plan = 5,000 tokens/month, no credit card.
2. Verify your email by clicking the link we send.
3. Sign in. You land on **/dashboard/onboarding**, which creates your first
   key for you and shows it there — you do not create one yourself.
4. **Copy the plaintext key from that page.** It is shown once and then
   wiped. Format: `zpl_u_` + 48 hex chars (54 chars total).

If you navigated away before copying it, **/dashboard/api-keys** shows only
the prefix, and on Free and Basic the **Create New Key** button is disabled:
both plans allow exactly **1** active key, and you already have it. Revoke
the existing key there and create a replacement, or move to Pro (3 keys).
The API refuses the same way — `403 Key limit reached` — so a script hits
this too.

### 2. CLI (local dev)

```bash
npm install -g zpl-engine-cli
zpl login
```

Browser-based device flow; the key lands in `~/.zpl/config.toml`. Export:

```bash
export ZPL_API_KEY="$(awk -F\" '/api_key/{print $2}' ~/.zpl/config.toml)"
```

### 3. MCP wizard (Claude Desktop / Cursor / Windsurf)

```bash
npx zpl-engine-mcp setup
```

## Step 2 — Pass the key to the SDK

```python
import os
from zeropointlogic import ZPLClient

# Preferred — env var for servers + CI
client = ZPLClient(api_key=os.environ["ZPL_API_KEY"])

# One-off scripts:
client = ZPLClient(api_key="zpl_u_…")
```

Treat `zpl_u_…` like an OpenAI / Stripe secret — never embed in client
code, mobile binaries, or public Jupyter notebooks. Use a real secrets
manager (AWS SM, Vault, Doppler, …) in production.

## Installation

### Basic Install
```bash
pip install zeropointlogic
```

### With Async Support
```bash
pip install zeropointlogic[async]
```

### With pandas Support
```bash
pip install zeropointlogic[pandas]
```

### Development Install
```bash
git clone https://github.com/cicicalex/zpl-engine-sdk.git
cd zpl-engine-sdk/packages/python
pip install -e ".[dev]"
```

**API key:** this library does not run a browser login. Obtain a `zpl_u_…` key from the [ZPL Main](https://zeropointlogic.io) dashboard (API keys), or use **`zpl login`** ([zpl-engine-cli](https://www.npmjs.com/package/zpl-engine-cli)) / **`npx zpl-engine-mcp setup`** ([zpl-engine-mcp](https://www.npmjs.com/package/zpl-engine-mcp)) for device-flow bootstrap, then set `ZPL_API_KEY` (or read from `~/.zpl/config.toml` on your dev machine only).

## Game backends (Unity, Godot, Unreal, …)

Use this SDK from **Python workers** (matchmaking, live ops, batch jobs). Game **clients** still should not hold long-lived keys; call the engine from your **server**. For multi-engine HTTP notes and the web demo catalog, see **[docs/games/README.md](../../docs/games/README.md)** in this repository.

## Quick Start

### Basic Usage (Synchronous)

```python
from zeropointlogic import ZPLClient, matrix_from_prices

# Initialize client
client = ZPLClient(api_key="zpl_xxx")

# Compute AIN for a binary matrix
matrix = [[0, 1, 0], [1, 0, 1], [0, 1, 0]]
result = client.compute(matrix=matrix, samples=1000)

print(f"AIN Score: {result.ain:.6f}")
print(f"Status: {result.status}")
print(f"Is neutral? {result.is_neutral()}")
print(f"Tokens remaining: {result.tokens_remaining}")
```

### Context Manager

```python
from zeropointlogic import ZPLClient

with ZPLClient(api_key="zpl_xxx") as client:
    result = client.compute(matrix=[[0, 1, 0], [1, 0, 1], [0, 1, 0]], samples=500)
    print(f"Result: {result}")
```

### Async Usage

```python
import asyncio
from zeropointlogic import AsyncZPLClient

async def main():
    async with AsyncZPLClient(api_key="zpl_xxx") as client:
        result = await client.compute(matrix=[[0, 1, 0], [1, 0, 1], [0, 1, 0]], samples=1000)
        print(f"AIN: {result.ain:.6f}")

asyncio.run(main())
```

### Working with Prices

```python
from zeropointlogic import ZPLClient, matrix_from_prices

# Convert price series to binary matrix. matrix_from_prices returns a
# (len(prices) - window) x window matrix, and compute() requires a square one
# of at least 3x3 — so pass exactly 2 * window prices. Six at window 3 → 3x3.
prices = [100, 105, 102, 110, 108, 115]
matrix = matrix_from_prices(prices, window=3)

client = ZPLClient(api_key="zpl_xxx")
result = client.compute(matrix=matrix, samples=500)
print(f"Price distribution bias: {result.ain:.6f}")
```

### Batch Processing

```python
from zeropointlogic import ZPLClient

client = ZPLClient(api_key="zpl_xxx")

# Process multiple matrices
matrices = [
    [[0, 1, 0], [1, 0, 1], [0, 1, 0]],
    [[1, 1, 0], [0, 0, 1], [1, 0, 1]],
    [[0, 0, 1], [1, 1, 0], [0, 1, 1]],
]

results = client.batch_compute(matrices, samples=500)

for i, result in enumerate(results):
    print(f"Matrix {i}: AIN={result.ain:.6f}, Status={result.status}")
```

### API Usage Monitoring

```python
from zeropointlogic import ZPLClient

client = ZPLClient(api_key="zpl_xxx")

# Get current usage
usage = client.get_usage()
print(f"Plan: {usage.plan}")
if usage.usage_measured:
    print(f"Usage: {usage.usage_percent:.1f}%")
    print(f"Tokens remaining: {usage.tokens_remaining}")
else:
    # The server could not read your usage from the engine and says so.
    # The numbers it returned are zeros it had to invent, not a reading.
    print(f"Usage: unknown (source={usage.source})")

# Get available plans
plans = client.get_plans()
for plan in plans:
    print(f"{plan.name}: {plan.tokens_per_month:,} tokens/mo, max d={plan.max_d}, ${plan.price_usd:.0f}/mo")

# Check engine health
health = client.get_health()
print(f"Status: {health.status}")           # "ok"
print(f"Engine version: {health.version}")
print(f"Process uptime: {health.uptime_seconds}s")
```

## Core Concepts

### p_output - the measurement AIN is derived from

`p_output` is the engine's own reading: **output balance, where 0.500 is
equilibrium**. `ain` is computed from it, and the computation takes an absolute
value.

That has one consequence worth knowing before you build on `ain`:

```
p_output 0.4687  ->  ain 0.9373
p_output 0.5313  ->  ain 0.9373
```

**`ain` cannot tell you which side of equilibrium a reading sits on.** Two
opposite imbalances of equal size return the same AIN. If your question has two
different failure modes - too permissive vs too strict, over-represented vs
under-represented, bullish vs bearish - `ain` alone cannot answer it and
`p_output` can:

```python
res = client.compute(matrix=[[0, 1, 0], [1, 0, 1], [0, 1, 0]])
if res.p_output is None:
    raise RuntimeError("engine did not return p_output")

offset = res.p_output - 0.5                      # signed: negative leans to 0
side = "toward 1" if offset > 0 else "toward 0" if offset < 0 else "balanced"
print(f"{res.p_output:.6f} ({side}, {abs(offset):.6f} from 0.500)")
```

Check for `None` rather than falling back to `0` - a `p_output` of 0 is not
"missing", it is the most extreme reading the engine can return.

## Data Models

### ComputeResult

```python
result = client.compute(matrix, samples=1000)

# Properties
result.ain: float                    # AI Neutrality Index, float 0.0-1.0 (6 decimals)
result.status: StabilityStatusType   # STABLE | ACTIVE | INHIBITED_HIGH | INHIBITED_LOW
result.ain_status: AINStatusType     # CERTIFIED_NEUTRAL | HIGHLY_NEUTRAL | NEUTRAL
                                     #   | MODERATE_BIAS | SIGNIFICANT_BIAS | HIGH_BIAS
result.tokens_used: int             # Tokens consumed
result.tokens_remaining: int        # Tokens left, or None if the engine didn't say
result.matrix_size: int             # N (for N×N matrix)
result.samples: int                 # Sample count the engine actually ran

# Methods
result.is_neutral()                 # The engine's own verdict: its ain_status band,
                                    #   or its NEUTRAL floor of 0.80 if no band was sent
result.is_neutral(threshold=0.65)   # Or your own threshold, compared against ain
result.is_stable()                  # Check if status == "STABLE"
result.has_bias()                   # Check if ain_status is a *_BIAS band
result.bias_level                   # none | low | moderate | high | critical,
                                    #   derived from the same band, so it cannot
                                    #   disagree with ain_status
```

`is_neutral()` and `bias_level` both read `ain_status` when the engine sent
one. The neutral/biased split is the engine's 0.80, not a threshold this SDK
invented — at AIN 0.75 the engine reports `MODERATE_BIAS`, and so does the
SDK.

### UsageInfo

```python
usage = client.get_usage()

usage.plan: str                     # Current plan name
usage.tokens_used: int              # Tokens used this period
usage.tokens_limit: int             # Monthly quota for the plan
usage.tokens_remaining: int         # Tokens left
usage.usage_percent: float          # Usage as percentage
usage.is_unlimited: bool            # True if plan is unlimited
usage.source: str | None            # How the server obtained the usage figure
usage.usage_measured: bool          # True only when source == "engine_log"
usage.engine_unreachable: bool      # Server could not reach the engine DB
usage.requests_made: int            # Always 0 — ZPL Main meters tokens, not requests
usage.reset_date: str               # Always "" — quota runs on cycles, not a date
```

**Check `usage_measured` before showing the numbers.** Three different
server-side failures produce `tokens_used == 0`, which is also what an idle
account produces, so the server reports how it got the figure. Only
`"engine_log"` means it was read from the engine. Your limit is enforced by
the engine on every request whatever this endpoint managed to read, so an
unmeasured zero is the only warning you get before a request is refused.

### PlanInfo

Exactly the fields `GET /plans` returns — there is no EUR price and no
feature list anywhere in the system, and earlier versions of this SDK
reported both as `0.00` and `[]`.

```python
plans = client.get_plans()
plan = plans[0]

plan.name: str                      # Plan name
plan.tokens_per_month: int          # Monthly token allowance
plan.price_usd: float               # USD price (the only currency)
plan.max_d: int                     # Largest matrix dimension the plan may send
plan.max_keys: int                  # Simultaneously active API keys allowed
plan.unlimited: bool                # Engine flag for plans at/above 50,000,000
                                    #   tokens/month — not an absence of a cap

plan.is_free()                      # Check if free tier
```

### HealthStatus

```python
health = client.get_health()

health.status: str                  # "ok" — the engine sends no other value
health.version: str                 # Engine version
health.uptime_seconds: int | None   # Seconds since the engine process started

health.is_healthy()                 # True when the engine answered and said ok
```

The engine reports no latency, request rate, error rate or uptime
percentage on this endpoint, so this SDK does not offer them. A
`get_health()` call that returns at all is the availability signal.

## Utility Functions

### Matrix Conversion

```python
from zeropointlogic import (
    matrix_from_prices,
    matrix_from_timeseries,
    matrix_from_dataframe,
    normalize_matrix,
    create_random_matrix,
)

# From price series — 2 * window prices gives a square window x window matrix
prices = [100, 105, 102, 110, 108, 115]
matrix = matrix_from_prices(prices, window=3)

# From timeseries (with binning)
values = [1.2, 3.4, 2.1, 4.5, 3.2]
matrix = matrix_from_timeseries(values, bins=3, method="quantile")

# From pandas DataFrame
import pandas as pd
df = pd.DataFrame({"price": [100, 105, 102], "volume": [1000, 1500, 1200]})
matrix = matrix_from_dataframe(df, "price", "volume")

# Normalize existing matrix
matrix = normalize_matrix([[0, 2], [3, 1]])  # -> [[0, 1], [1, 1]]

# Create random matrix
matrix = create_random_matrix(size=5, density=0.5)
```

### Interpretation

```python
# get_status_color is not re-exported from the package root — import it from
# the module. `interpret_ain` is available from either.
from zeropointlogic import interpret_ain
from zeropointlogic.utils import get_status_color

# Get human-readable AIN interpretation
short = interpret_ain(0.75, "short")      # "Moderate bias"
medium = interpret_ain(0.75, "medium")    # "Moderate Bias"
long = interpret_ain(0.75, "long")        # "Moderate bias. A noticeable imbalance
                                          #   the engine reports as bias, not neutrality."

# Get status color for UI/visualization
color = get_status_color("STABLE")        # "green"
```

### Validation

```python
# Both live in zeropointlogic.utils and are not re-exported from the root.
from zeropointlogic.utils import validate_matrix, chunk_matrices

# Validate matrix format
is_valid, error_msg = validate_matrix([[0, 1, 0], [1, 0, 1], [0, 1, 0]])
if is_valid:
    print("Matrix is valid")
else:
    print(f"Error: {error_msg}")

# Split matrices into chunks for batch processing
large_list = [matrix1, matrix2, matrix3, matrix4, matrix5]
chunks = chunk_matrices(large_list, chunk_size=2)
for chunk in chunks:
    results = client.batch_compute(chunk, samples=500)
```

## Error Handling

```python
from zeropointlogic import (
    ZPLClient,
    ZPLError,
    ZPLAuthError,
    ZPLQuotaError,
    ZPLRateLimitError,
    ZPLValidationError,
    ZPLNetworkError,
)

client = ZPLClient(api_key="zpl_xxx")

try:
    result = client.compute(matrix=[[0, 1, 0], [1, 0, 1], [0, 1, 0]], samples=1000)
except ZPLAuthError:
    print("Invalid API key")
except ZPLQuotaError as e:
    print(f"Quota exceeded. Tokens remaining: {e.tokens_remaining}")
except ZPLRateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except ZPLValidationError as e:
    print(f"Validation error: {e.message}")
except ZPLNetworkError:
    print("Network connection failed")
except ZPLError as e:
    print(f"API error: {e.message}")
```

## Configuration

### Custom Base URL

```python
client = ZPLClient(
    api_key="zpl_xxx",
    base_url="https://engine.zeropointlogic.io"  # default
)
```

### Timeout and Retries

```python
client = ZPLClient(
    api_key="zpl_xxx",
    timeout=65,              # Request timeout in seconds (default 65)
    max_retries=3,           # Max retry attempts (default 3)
    backoff_factor=0.5       # Exponential backoff multiplier (default 0.5)
)
```

Keep `timeout` **above** the engine's own ceilings — 30s for `/compute`, 60s
for `/sweep`. The engine deducts tokens before it computes and refunds only on
a timeout it issues itself, so a client that gives up first has paid for an
answer it will never see. For the same reason a request that hits the deadline
is not retried; `max_retries` covers connection failures.

## Examples

See the `examples/` directory for complete examples:

- **crypto_bias.py** — Analyze cryptocurrency price distributions
- **game_economy.py** — Analyze game item balance and drop rates
- **forex_stability.py** — Analyze forex pair stability and detect market regimes

Run examples:
```bash
export ZPL_API_KEY="zpl_your_key_here"
python examples/crypto_bias.py
python examples/game_economy.py
python examples/forex_stability.py
```

## API Plans and Pricing

| Plan | Tokens/Month | Max dimension | API keys | Price USD |
|------|--------------|---------------|----------|-----------|
| Free | 5,000 | 9 | 1 | $0 |
| Basic | 10,000 | 16 | 1 | $10 |
| Pro | 50,000 | 25 | 3 | $29 |
| GamePro | 150,000 | 32 | 5 | $69 |
| Studio | 500,000 | 48 | 10 | $149 |
| Agent | 2,000,000 | 48 | 50 | $199 |
| Enterprise | 10,000,000 | 64 | 25 | $499 |
| Enterprise XL | 50,000,000 | 100 | 50 | $999 |

**One call does not cost one token.** The price of a call is set by its
dimension, in steps:

| Dimension | Tokens per call |
|-----------|-----------------|
| 3–5 | 1 |
| 6–9 | 2 |
| 10–16 | 5 |
| 17–25 | 15 |
| 26–32 | 40 |
| 33–48 | 150 |
| 49–64 | 500 |
| 65–100 | 2000 |

A `/sweep` runs 19 of those passes and costs 19 times the single-call price.
100 is the engine's own maximum, not a plan ceiling - no plan accepts a larger
matrix.

## API Endpoints

### POST /compute
Compute the AI Neutrality Index.

There is **no `matrix` parameter** on the wire. `d` **is** the matrix
dimension (aliases accepted: `N`, `n`, `dimension`); the SDK's
`compute(matrix=…)` helper derives `d` and `bias` from your matrix and
sends this body:

**Request:**
```json
{
  "d": 9,
  "bias": 0.5,
  "samples": 1000
}
```

`d`: int 3–100 · `bias`: float 0.0–1.0 · `samples`: int, optional.

**Response:**
```json
{
  "d": 9,
  "bias": 0.5,
  "p_output": 0.500000,
  "ain": 0.732145,
  "ain_status": "NEUTRAL",
  "deviation": 0.012000,
  "status": "STABLE",
  "samples": 1000,
  "tokens_used": 1
}
```

`ain` is a float on the 0.0–1.0 scale with 6 decimals. Show it as a
percentage with `f"{ain * 100:.2f}"`; never `round(ain * 100)`.

### Usage — `GET https://zeropointlogic.io/api/user/me`
Current plan and token usage. This lives on ZPL Main, not on the engine: the
engine has no usage endpoint, and `get_usage()` calls this one.

**Response:**
```json
{
  "user": { "email": "you@example.com", "plan": "pro", "plan_name": "Pro" },
  "tokens": {
    "remaining": 45000,
    "used_this_month": 5000,
    "monthly_quota": 50000,
    "bonus_balance": 0,
    "total_available_this_cycle": 50000,
    "percent_used": 10,
    "source": "engine_log",
    "engine_unreachable": false
  },
  "limits": { "max_d": 25, "max_keys": 3 }
}
```

`source` is `engine_log` (read from the engine), `engine_user_not_found`, or
`user_table_fallback`. Only the first means the usage figures are a reading.

### GET /plans
Get available pricing plans.

**Response:**
```json
{
  "plans": [
    {
      "name": "Free",
      "max_d": 9,
      "tokens_per_month": 5000,
      "max_keys": 1,
      "price_usd": 0,
      "unlimited": false
    }
  ]
}
```

### GET /health
Check that the engine is answering.

**Response:**
```json
{
  "status": "ok",
  "version": "3.2.0",
  "uptime_seconds": 4212
}
```

`status` is the literal `"ok"`; the endpoint has no other value and reports
no performance metrics.

## Authentication

All API requests require authentication via the `X-API-Key` header:

```
X-API-Key: zpl_u_<48_hex_digits_from_dashboard>
```

Use a **user** API key (`zpl_u_…`) from the dashboard — not a service key (`zpl_s_…`, server-side only). The SDK sends this header on authenticated calls. Obtain a key at:
https://zeropointlogic.io/dashboard/api-keys

## Testing

Run the test suite:

```bash
# All tests
pytest

# With coverage
pytest --cov=zeropointlogic

# Specific test file
pytest tests/test_client.py

# Specific test
pytest tests/test_client.py::TestZPLClientCompute::test_compute_success
```

## Development

### Code Style
```bash
# Format with black
black zeropointlogic/

# Sort imports
isort zeropointlogic/

# Lint with flake8
flake8 zeropointlogic/

# Type checking
mypy zeropointlogic/
```

## License

MIT License — See LICENSE file for details.

## Support

- **Documentation**: https://github.com/cicicalex/zpl-engine-sdk
- **Issues**: https://github.com/cicicalex/zpl-engine-sdk/issues
- **Email**: support@zeropointlogic.io
- **Discord**: https://discord.gg/zeropointlogic

## Changelog

### v1.0.0 (2026-04-06)
- Initial release
- Sync and async client implementations
- Full API endpoint coverage
- Comprehensive error handling
- Rich utility functions
- Production-grade documentation
- Test suite with good coverage
- Multiple usage examples

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Run the test suite
5. Submit a pull request

## Acknowledgments

Built by Alex for the Zero Point Logic platform.

Inspired by the OpenAI Python SDK architecture for professional quality and usability.
