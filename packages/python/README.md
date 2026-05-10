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

print(f"AIN Score: {result.ain:.3f}")
print(f"Status: {result.status}")
print(f"Is neutral? {result.is_neutral()}")
print(f"Tokens remaining: {result.tokens_remaining}")
```

### Context Manager

```python
from zeropointlogic import ZPLClient

with ZPLClient(api_key="zpl_xxx") as client:
    result = client.compute(matrix=[[0, 1], [1, 0]], samples=500)
    print(f"Result: {result}")
```

### Async Usage

```python
import asyncio
from zeropointlogic import AsyncZPLClient

async def main():
    async with AsyncZPLClient(api_key="zpl_xxx") as client:
        result = await client.compute(matrix=[[0, 1], [1, 0]], samples=1000)
        print(f"AIN: {result.ain:.3f}")

asyncio.run(main())
```

### Working with Prices

```python
from zeropointlogic import ZPLClient, matrix_from_prices

# Convert price series to binary matrix
prices = [100, 105, 102, 110, 108, 115, 112]
matrix = matrix_from_prices(prices, window=3)

client = ZPLClient(api_key="zpl_xxx")
result = client.compute(matrix=matrix, samples=500)
print(f"Price distribution bias: {result.ain:.3f}")
```

### Batch Processing

```python
from zeropointlogic import ZPLClient

client = ZPLClient(api_key="zpl_xxx")

# Process multiple matrices
matrices = [
    [[0, 1], [1, 0]],
    [[1, 1], [0, 0]],
    [[0, 0], [1, 1]],
]

results = client.batch_compute(matrices, samples=500)

for i, result in enumerate(results):
    print(f"Matrix {i}: AIN={result.ain:.3f}, Status={result.status}")
```

### API Usage Monitoring

```python
from zeropointlogic import ZPLClient

client = ZPLClient(api_key="zpl_xxx")

# Get current usage
usage = client.get_usage()
print(f"Plan: {usage.plan}")
print(f"Usage: {usage.usage_percent:.1f}%")
print(f"Tokens remaining: {usage.tokens_remaining}")

# Get available plans
plans = client.get_plans()
for plan in plans:
    print(f"{plan.name}: {plan.tokens_per_month:,} tokens/mo")

# Check engine health
health = client.get_health()
print(f"Status: {health.status}")
print(f"Uptime: {health.uptime_percent:.2f}%")
```

## Data Models

### ComputeResult

```python
result = client.compute(matrix, samples=1000)

# Properties
result.ain: float                    # AI Neutrality Index (0-1)
result.p_output: float              # Probability output
result.deviation: float             # Standard deviation
result.status: AIStatusType         # CERTIFIED_NEUTRAL | STABLE | MODERATE_BIAS | HIGH_BIAS | CRITICAL_BIAS
result.tokens_used: int             # Tokens consumed
result.tokens_remaining: int        # Tokens left
result.matrix_size: int             # N (for N×N matrix)
result.samples: int                 # Sample count used

# Methods
result.is_neutral(threshold=0.7)    # Check if AIN >= threshold
result.is_stable()                  # Check if status is neutral/stable
result.has_bias()                   # Check if status contains BIAS
```

### UsageInfo

```python
usage = client.get_usage()

usage.plan: str                     # Current plan name
usage.tokens_used: int              # Tokens used this period
usage.tokens_limit: int             # Total tokens available
usage.tokens_remaining: int         # Tokens left
usage.usage_percent: float          # Usage as percentage
usage.is_unlimited: bool            # True if plan is unlimited
usage.requests_made: int            # API requests made
usage.reset_date: str               # When tokens reset
```

### PlanInfo

```python
plans = client.get_plans()
plan = plans[0]

plan.name: str                      # Plan name
plan.tokens_per_month: int          # Monthly token allowance
plan.price_usd: float               # USD price
plan.price_eur: float               # EUR price
plan.features: list[str]            # Included features

plan.is_free()                      # Check if free tier
```

### HealthStatus

```python
health = client.get_health()

health.status: str                  # "up" | "degraded" | "down"
health.uptime_percent: float        # Uptime percentage
health.response_time_ms: float      # Avg response time
health.requests_per_second: float   # Current RPS
health.error_rate_percent: float    # Error rate
health.version: str                 # Engine version

health.is_healthy()                 # Check if up and >99% uptime
```

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

# From price series
prices = [100, 105, 102, 110]
matrix = matrix_from_prices(prices, window=2)

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
from zeropointlogic import interpret_ain, get_status_color

# Get human-readable AIN interpretation
short = interpret_ain(0.75, "short")       # "Excellent"
medium = interpret_ain(0.75, "medium")    # "Highly Neutral"
long = interpret_ain(0.75, "long")        # Full explanation

# Get status color for UI/visualization
color = get_status_color("STABLE")        # "green"
```

### Validation

```python
from zeropointlogic import validate_matrix, chunk_matrices

# Validate matrix format
is_valid, error_msg = validate_matrix([[0, 1], [1, 0]])
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
    result = client.compute(matrix=[[0, 1], [1, 0]], samples=1000)
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
    timeout=30,              # Request timeout in seconds (default 30)
    max_retries=3,           # Max retry attempts (default 3)
    backoff_factor=0.5       # Exponential backoff multiplier (default 0.5)
)
```

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

| Plan | Tokens/Month | Price USD | Price EUR |
|------|--------------|-----------|-----------|
| Free | 100 | $0 | €0 |
| Basic | 10,000 | $10 | €9 |
| Pro | 50,000 | $29 | €27 |
| GamePro | 150,000 | $69 | €63 |
| Studio | 500,000 | $149 | €137 |
| Agent | 2,000,000 | $199 | €183 |
| Enterprise | 10,000,000 | $499 | €459 |
| XL | Unlimited | $999 | €919 |

**1 token = 1 compute operation**

## API Endpoints

### POST /compute
Analyze a binary matrix for AI Neutrality Index.

**Request:**
```json
{
  "matrix": [[0, 1, 0], [1, 0, 1], [0, 1, 0]],
  "samples": 1000
}
```

**Response:**
```json
{
  "ain": 0.73,
  "p_output": 0.51,
  "deviation": 0.12,
  "status": "STABLE",
  "tokens_used": 1,
  "tokens_remaining": 9999
}
```

### GET /usage
Get current API usage for authenticated key.

**Response:**
```json
{
  "plan": "pro",
  "tokens_used": 5000,
  "tokens_limit": 50000,
  "tokens_remaining": 45000,
  "reset_date": "2026-05-06",
  "requests_made": 150,
  "last_reset": "2026-04-06"
}
```

### GET /plans
Get available pricing plans.

**Response:**
```json
{
  "plans": [
    {
      "name": "Free",
      "tokens_per_month": 100,
      "price_usd": 0.0,
      "price_eur": 0.0,
      "features": ["API access", "5 requests/min"]
    }
  ]
}
```

### GET /health
Check engine health and performance.

**Response:**
```json
{
  "status": "up",
  "uptime_percent": 99.95,
  "response_time_ms": 45.2,
  "requests_per_second": 150.5,
  "error_rate_percent": 0.05,
  "version": "1.2.3"
}
```

## Authentication

All API requests require authentication via the `X-API-Key` header:

```
X-API-Key: zpl_s_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

The SDK automatically includes this header. Obtain an API key at:
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

Built by Alex Cicic for the Zero Point Logic platform.

Inspired by the OpenAI Python SDK architecture for professional quality and usability.
