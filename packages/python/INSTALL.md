# Installation & Setup Guide

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Virtual environment (recommended)

## Quick Install

### 1. Clone or Download

```bash
cd path/to/zpl-engine-sdk/packages/python
```

### 2. Create Virtual Environment (Optional but Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Package

#### From Source (Development)
```bash
pip install -e .
```

#### With All Optional Dependencies
```bash
pip install -e ".[async,pandas,dev]"
```

#### Specific Extras
```bash
pip install -e ".[async]"    # For async support (httpx)
pip install -e ".[pandas]"   # For DataFrame support
pip install -e ".[dev]"      # For development (pytest, black, mypy)
```

### 4. Verify Installation

```python
python3 -c "import zeropointlogic; print(f'ZPL SDK v{zeropointlogic.__version__}')"
```

Expected output:
```
ZPL SDK v1.0.0
```

## PyPI Installation (When Published)

Once published to PyPI:

```bash
pip install zeropointlogic
pip install zeropointlogic[async]
pip install zeropointlogic[pandas]
pip install zeropointlogic[dev]
```

## Setup Configuration

### 1. Get API Key

1. Visit https://zeropointlogic.io/dashboard
2. Create API key (**user** key starts with `zpl_u_`; `zpl_s_` is server-side only)
3. Save securely

### 2. Configure Environment

#### Option A: Environment Variable
```bash
export ZPL_API_KEY="zpl_u_your_key_here"
```

#### Option B: Code
```python
import os
from zeropointlogic import ZPLClient

api_key = "zpl_u_your_key_here"  # Or from env
client = ZPLClient(api_key=api_key)
```

#### Option C: .env File
```bash
# Create .env file
echo 'ZPL_API_KEY="zpl_u_your_key_here"' > .env

# Load in Python
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("ZPL_API_KEY")
```

## Verification

### Test Installation

```python
from zeropointlogic import ZPLClient

# Use a real dashboard key in production; placeholder will fail auth on the engine.
client = ZPLClient(api_key="zpl_u_invalid_placeholder")

# Check available plans
try:
    plans = client.get_plans()
    print(f"SDK working! Found {len(plans)} plans")
except Exception as e:
    print(f"Note: {e}")  # Expected if key is invalid
```

### Run Tests

```bash
# Install test dependencies if not already done
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=zeropointlogic

# Run specific test file
pytest tests/test_client.py
```

### Run Examples

```bash
# Set your API key first
export ZPL_API_KEY="zpl_u_your_key_here"

# Run examples
python examples/crypto_bias.py
python examples/game_economy.py
python examples/forex_stability.py
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'zeropointlogic'"

**Solution:**
```bash
# Make sure you're in the package directory (e.g. zpl-engine-sdk/packages/python)

# Install in development mode
pip install -e .

# Or add to PYTHONPATH (use your local clone path)
# export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Issue: "No module named 'requests'"

**Solution:**
```bash
pip install requests>=2.28.0
```

### Issue: "No module named 'httpx'" (for async)

**Solution:**
```bash
pip install httpx>=0.24.0
```

### Issue: "No module named 'pandas'" (for DataFrame support)

**Solution:**
```bash
pip install pandas>=1.5.0
```

## Development Setup

For contributing or modifying the SDK:

```bash
# Install with all dev tools
pip install -e ".[dev]"

# Format code with black
black zeropointlogic/

# Sort imports with isort
isort zeropointlogic/

# Lint with flake8
flake8 zeropointlogic/

# Type check with mypy
mypy zeropointlogic/

# Run tests with coverage
pytest --cov=zeropointlogic tests/
```

## Docker Setup (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install -e ".[async,pandas]"

CMD ["python"]
```

Build and run:

```bash
docker build -t zpl-sdk .
docker run -it -e ZPL_API_KEY="zpl_u_xxx" zpl-sdk
```

## Integration in Existing Project

### In Another Python Package

```bash
# Add to requirements.txt
zeropointlogic>=1.0.0
zeropointlogic[async]>=1.0.0  # If you need async

# Or in setup.py
install_requires=[
    'zeropointlogic>=1.0.0',
]

extras_require={
    'async': ['zeropointlogic[async]>=1.0.0'],
}
```

### Usage in Your Code

```python
from zeropointlogic import ZPLClient, matrix_from_prices

client = ZPLClient(api_key="your_key")
prices = [100, 105, 102, 110]
matrix = matrix_from_prices(prices, window=2)
result = client.compute(matrix=matrix, samples=500)
```

## Updating

To update to latest version:

```bash
# If installed from source
cd path/to/zpl-engine-sdk/packages/python
git pull
pip install -e . --upgrade

# If installed from PyPI
pip install --upgrade zeropointlogic
```

## Uninstall

```bash
pip uninstall zeropointlogic
```

## Next Steps

1. Read the [QUICKSTART.md](QUICKSTART.md) guide
2. Check out [examples/](examples/) directory
3. Review [README.md](README.md) for full API reference
4. Run tests to verify everything works
5. Start building with the SDK!

## Support

- **Docs**: See README.md and QUICKSTART.md
- **Issues**: Check GitHub issues
- **Email**: support@zeropointlogic.io

Happy analyzing!
