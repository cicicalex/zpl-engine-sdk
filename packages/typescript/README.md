# ZPL Engine TypeScript SDK

Official TypeScript SDK for the [Zero Point Logic Engine API](https://engine.zeropointlogic.io) — an AI Neutrality Index (AIN) calculator for stability and bias analysis.

## Features

- **AIN Computation**: Calculate AI Neutrality Index for binary matrices
- **Batch Processing**: Analyze multiple matrices concurrently
- **Retry Logic**: Built-in exponential backoff with jitter
- **Type Safe**: Full TypeScript strict mode support
- **Zero Dependencies**: Core SDK has no external dependencies
- **Browser Compatible**: Works in Node.js 18+ and modern browsers
- **Tree Shakeable**: Only import what you need

## Installation

```bash
npm install @zeropointlogic/sdk
```

**API key:** no built-in login flow (same pattern as Stripe/OpenAI SDKs). Get a `zpl_u_…` key from the [ZPL Main](https://zeropointlogic.io) dashboard (API keys), or bootstrap with **`zpl login`** ([zpl-engine-cli](https://www.npmjs.com/package/zpl-engine-cli)) / **`npx zpl-engine-mcp setup`** ([zpl-engine-mcp](https://www.npmjs.com/package/zpl-engine-mcp)), then pass the key via `process.env.ZPL_API_KEY` or your secret manager.

## Game backends (Unity, Godot, Unreal, …)

This package targets **Node.js** and bundlers. Game **clients** usually do not embed it; your **authoritative server** (or a Node sidecar) calls the engine. For engine-specific HTTP patterns, demo catalog, and neutrality-as-decision-layer context, see **[docs/games/README.md](../../docs/games/README.md)** in this repository.

## Quick Start

```typescript
import { ZPLClient, createRandomMatrix } from '@zeropointlogic/sdk';

const client = new ZPLClient({
  apiKey: 'zpl_your_api_key_here',
});

// Analyze a binary matrix
const matrix = createRandomMatrix(16);
const result = await client.compute({
  matrix,
  samples: 1000,
});

console.log(`AIN Score: ${result.ain}`);      // 0.73
console.log(`Status: ${result.status}`);      // 'STABLE'
console.log(`Is Neutral: ${result.isNeutral}`); // true
```

## Core Concepts

### AIN (AI Neutrality Index)

A mathematical score (0-1) indicating how neutral/unbiased data is:

- **0.8-1.0**: Excellent neutrality (CERTIFIED_NEUTRAL)
- **0.7-0.8**: Good neutrality (STABLE)
- **0.5-0.7**: Moderate bias (MODERATE_BIAS)
- **0.3-0.5**: High bias (HIGH_BIAS)
- **0.0-0.3**: Critical bias (CRITICAL_BIAS)

### Binary Matrix

Input data for AIN calculation. An N×N matrix where each element is 0 or 1.

**Examples:**
- Price direction matrix: 1 = up, 0 = down
- Win/loss matrix: 1 = win, 0 = loss
- Boolean state matrix: 1 = true, 0 = false

## API Documentation

### Client Initialization

```typescript
const client = new ZPLClient({
  apiKey: 'zpl_xxx',                    // Required
  baseUrl: 'https://engine.zeropointlogic.io', // Optional
  timeout: 30000,                       // Optional (ms)
  retries: 3,                           // Optional
  debug: false,                         // Optional
});
```

### compute()

Run AIN computation on a single matrix.

```typescript
const result = await client.compute({
  matrix: [[0, 1], [1, 0]],
  samples: 1000,                        // Optional (default: 1000)
  timeout: 30000,                       // Optional
});

// result: ComputeResult
// {
//   ain: 0.73,
//   status: 'STABLE',
//   isNeutral: true,
//   biasLevel: 'low',
//   tokensUsed: 1,
//   tokensRemaining: 999,
//   ...
// }
```

### batchCompute()

Analyze multiple matrices with concurrency control.

```typescript
const results = await client.batchCompute(
  [matrix1, matrix2, matrix3],
  {
    samples: 500,
    concurrency: 2,           // Process 2 at a time
    stopOnError: false,       // Continue on errors
  }
);

// results: BatchComputeResult
// {
//   results: [ComputeResult, ComputeResult, ...],
//   totalTokensUsed: 3,
//   totalTokensRemaining: 997,
//   completedAt: Date,
// }
```

### getUsage()

Get current token quota and usage.

```typescript
const usage = await client.getUsage();

// {
//   plan: 'pro',
//   dailyLimit: 10000,
//   monthlyLimit: 300000,
//   usedToday: 150,
//   usedThisMonth: 5000,
//   tokensRemainingToday: 9850,
//   tokensRemainingMonth: 295000,
//   resetAtToday: '2024-01-15T00:00:00Z',
//   resetAtMonth: '2024-02-01T00:00:00Z',
// }
```

### getPlans()

List all available plans and pricing.

```typescript
const plans = await client.getPlans();

// {
//   plans: [
//     { id: 'free', name: 'Free', price: 0, dailyLimit: 10, ... },
//     { id: 'basic', name: 'Basic', price: 10, dailyLimit: 1000, ... },
//     // ...
//   ],
//   fetchedAt: Date,
// }
```

### getHealth()

Check API health status.

```typescript
const health = await client.getHealth();

// {
//   status: 'healthy',
//   uptime: 99.99,
//   version: '1.0.0',
//   timestamp: '2024-01-15T12:34:56Z',
// }
```

## Utility Functions

### pricesToMatrix()

Convert price array to binary matrix.

```typescript
import { pricesToMatrix } from '@zeropointlogic/sdk';

const prices = [100, 102, 101, 103, 105];
const matrix = pricesToMatrix(prices, 20); // window size 20
```

### matrixFromReturns()

Convert returns array to binary matrix.

```typescript
import { matrixFromReturns } from '@zeropointlogic/sdk';

const returns = [0.02, -0.01, 0.03, 0.01];
const matrix = matrixFromReturns(returns);
```

### createRandomMatrix()

Generate random binary matrix (for testing).

```typescript
import { createRandomMatrix } from '@zeropointlogic/sdk';

const matrix = createRandomMatrix(16);        // 16x16 matrix
const seeded = createRandomMatrix(16, 12345); // Deterministic with seed
```

### interpretAIN()

Get human-readable interpretation of AIN score.

```typescript
import { interpretAIN } from '@zeropointlogic/sdk';

console.log(interpretAIN(0.85));
// "Excellent neutrality. System maintains strong neutral properties..."
```

### ainToBiasLevel()

Convert AIN score to bias classification.

```typescript
import { ainToBiasLevel } from '@zeropointlogic/sdk';

ainToBiasLevel(0.85); // 'none'
ainToBiasLevel(0.72); // 'low'
ainToBiasLevel(0.55); // 'moderate'
```

## Error Handling

The SDK provides specific error types for different failure scenarios:

```typescript
import {
  ZPLClient,
  ZPLAuthError,
  ZPLRateLimitError,
  ZPLQuotaExceededError,
  ZPLValidationError,
  ZPLTimeoutError,
  ZPLNetworkError,
} from '@zeropointlogic/sdk';

try {
  const result = await client.compute({ matrix, samples: 1000 });
} catch (error) {
  if (error instanceof ZPLAuthError) {
    console.error('Invalid API key');
  } else if (error instanceof ZPLQuotaExceededError) {
    console.error(`Need ${error.getTokensNeeded()} more tokens`);
  } else if (error instanceof ZPLRateLimitError) {
    console.error(`Retry after ${error.getRetryDelayMs()}ms`);
  } else if (error instanceof ZPLValidationError) {
    console.error('Invalid input:', error.message);
  } else if (error instanceof ZPLTimeoutError) {
    console.error('Request timed out');
  } else if (error instanceof ZPLNetworkError) {
    console.error('Network error:', error.message);
  }
}
```

## Examples

### Crypto Market Analysis

```typescript
import { ZPLClient, pricesToMatrix } from '@zeropointlogic/sdk';

const client = new ZPLClient({ apiKey: 'zpl_xxx' });

const btcPrices = [45230, 45890, 44950, /* ... */];
const matrix = pricesToMatrix(btcPrices, 15);

const result = await client.compute({ matrix, samples: 5000 });

if (result.ain >= 0.7) {
  console.log('Market shows balanced behavior');
} else {
  console.log('Market shows directional bias');
}
```

### Game Economy Analysis

```typescript
import { ZPLClient, createRandomMatrix } from '@zeropointlogic/sdk';

const client = new ZPLClient({ apiKey: 'zpl_xxx' });

const economySystems = {
  dropRates: createRandomMatrix(20),
  wealthCurve: createRandomMatrix(25),
  pvpBalance: createRandomMatrix(16),
};

for (const [name, matrix] of Object.entries(economySystems)) {
  const result = await client.compute({ matrix, samples: 2000 });
  console.log(`${name}: ${result.status}`);
}
```

### Batch Analysis with Error Handling

```typescript
import { ZPLClient, createRandomMatrix } from '@zeropointlogic/sdk';

const client = new ZPLClient({ apiKey: 'zpl_xxx' });

const matrices = Array(10)
  .fill(null)
  .map(() => createRandomMatrix(16));

try {
  const batch = await client.batchCompute(matrices, {
    samples: 500,
    concurrency: 3,
    stopOnError: false,
  });

  console.log(`Completed: ${batch.results.length} analyses`);
  console.log(`Tokens used: ${batch.totalTokensUsed}`);
} catch (error) {
  console.error('Batch processing failed:', error);
}
```

## Browser Usage

```typescript
// React example
import { ZPLClient, pricesToMatrix } from '@zeropointlogic/sdk';

function MarketAnalysis() {
  const [result, setResult] = React.useState(null);

  const analyze = async () => {
    const client = new ZPLClient({
      apiKey: process.env.REACT_APP_ZPL_KEY,
    });

    const prices = [100, 102, 101, 103, 105];
    const matrix = pricesToMatrix(prices);
    const res = await client.compute({ matrix, samples: 1000 });

    setResult(res);
  };

  return (
    <div>
      <button onClick={analyze}>Analyze</button>
      {result && <p>AIN: {result.ain.toFixed(4)}</p>}
    </div>
  );
}
```

## Configuration & Environment

Use environment variables for API keys:

```bash
# .env
ZPL_API_KEY=zpl_xxx
```

```typescript
const client = new ZPLClient({
  apiKey: process.env.ZPL_API_KEY,
});
```

## Performance Tips

1. **Batch Processing**: Use `batchCompute()` for multiple matrices
2. **Concurrency**: Control concurrency to balance speed vs. rate limits
3. **Samples**: Use lower samples (500-1000) for fast iterations, higher (5000+) for analysis
4. **Caching**: Cache results for unchanged data
5. **Retry Strategy**: Exponential backoff is automatic but tunable via config

## Rate Limiting & Quotas

The SDK automatically handles:
- **Retry logic** with exponential backoff (3 attempts by default)
- **Rate limit detection** (HTTP 429)
- **Quota exhaustion** (HTTP 402) with token tracking
- **Timeout management** (30s default)

## Troubleshooting

### "Invalid API key" error
Check that your API key is correct and has not expired.

### Rate limit errors (429)
The SDK retries automatically, but if you hit this frequently:
- Reduce batch size
- Increase concurrency delays
- Upgrade to a higher plan

### Token quota exceeded (402)
You've exceeded your plan's monthly/daily limit. Upgrade your plan or wait for quota reset.

### Timeout errors
Increase `timeout` in client config or reduce matrix size/samples:

```typescript
const client = new ZPLClient({
  apiKey: 'zpl_xxx',
  timeout: 60000, // 60 seconds
});
```

## Types

All types are exported from the root module:

```typescript
import type {
  AINStatus,
  BiasLevel,
  ComputeResult,
  BatchComputeResult,
  Usage,
  Plan,
  HealthResponse,
  ZPLClientConfig,
} from '@zeropointlogic/sdk';
```

## Building & Testing

```bash
# Install dependencies
npm install

# Build TypeScript
npm run build

# Type checking
npm run type-check

# Watch mode
npm run build:watch
```

## License

MIT

## Support

For issues, questions, or feature requests:
- GitHub: https://github.com/zeropointlogic/sdk-ts
- Email: support@zeropointlogic.io
- Docs: https://zeropointlogic.io/docs

## See Also

- [ZPL Engine API Docs](https://engine.zeropointlogic.io/docs)
- [Finance Monitor](https://finance.zeropointlogic.io)
- [ZPL Main](https://zeropointlogic.io)
