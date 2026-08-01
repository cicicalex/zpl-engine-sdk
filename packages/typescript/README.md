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

## v2.0.0 — BREAKING + REQUIRED UPGRADE

v1.x sent `{matrix, samples}` to the engine, which the Rust API rejected
with `400 Failed to deserialize: missing field 'bias'`. Every single v1.x
call failed on the wire. v2.0.0 fixes the body shape and is the first
working release.

**Upgrade immediately:** `npm install @zeropointlogic/sdk@latest`

Public API surface (`client.compute({ matrix, samples })`) is unchanged.
Under the hood we now compute `d = matrix.length` and `bias =
sum_of_1s / (d*d)` and post `{d, bias, samples}` to the engine.

## Installation

```bash
npm install @zeropointlogic/sdk
```

## Step 1 — Get an API key (DO THIS FIRST)

This SDK is a thin HTTP client (same shape as Stripe / OpenAI SDKs). It
does **not** log you in, register an account, or mint a key for you.
Calling `client.compute(...)` without a valid `zpl_u_…` user key returns
`401 Unauthorized` immediately.

You must obtain a key first, by ONE of these three paths:

### 1. Dashboard (recommended for server/app use)

1. Go to **<https://zeropointlogic.io/auth/register>** and create an
   account. Free plan = 5,000 tokens/month, no credit card required.
2. Verify your email by clicking the link we send (verification gates
   dashboard access).
3. Sign in. You land on **/dashboard/onboarding**, which creates your first
   key for you and displays it there — you do not create one yourself.
4. **Copy the plaintext key from that page.** It is shown once and then
   wiped. It looks like `zpl_u_<48 hex chars>` (54 chars total).

Missed it? **/dashboard/api-keys** shows only the prefix, and on Free and
Basic the **Create New Key** button is disabled: both plans allow exactly
**1** active key and you already have it. Revoke the existing key there and
create a replacement, or move to Pro (3 keys). `POST /api/keys` enforces the
same cap with `403 Key limit reached`, so scripting around the button does
not help.

### 2. CLI (for local dev)

```bash
npm install -g zpl-engine-cli
zpl login
```

Opens a browser device-flow page; after you approve, the key is written
to `~/.zpl/config.toml`. Export with:

```bash
export ZPL_API_KEY="$(awk -F\" '/api_key/{print $2}' ~/.zpl/config.toml)"
```

### 3. MCP wizard (for Claude Desktop / Cursor / Windsurf)

```bash
npx zpl-engine-mcp setup
```

Same device-flow; auto-patches all detected MCP client configs.

## Step 2 — Pass the key to the SDK

```ts
import { ZPLClient } from '@zeropointlogic/sdk';

// Preferred: pull from env (servers + CI)
const client = new ZPLClient({ apiKey: process.env.ZPL_API_KEY! });

// One-off scripts:
const client2 = new ZPLClient({ apiKey: 'zpl_u_…' });
```

> **Browser bundles:** never ship a personal `zpl_u_…` key in a public
> client bundle. Proxy through your own backend, or mint a short-lived
> per-request token if you really need browser-side calls. Treat
> `zpl_u_…` like an OpenAI / Stripe secret.

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

console.log(`AIN Score: ${result.ain}`);        // 0.73
console.log(`Status: ${result.status}`);        // 'STABLE' (stability regime)
console.log(`Band: ${result.ainStatus}`);       // 'MODERATE_BIAS'
console.log(`Is Neutral: ${result.isNeutral}`); // false — 0.73 is below the
                                                // engine's NEUTRAL floor of 0.80
```

## Core Concepts

### AIN (AI Neutrality Index)

A float on the **0.0 – 1.0** scale with **6 decimals**, indicating how
neutral/unbiased data is. Display it as a percentage with
`(ain * 100).toFixed(2)` — never `Math.round(ain * 100)`, which discards
4 of the 6 decimals.

### The two status fields — do not mix them

`ainStatus` (`ain_status` on the wire) is the **AIN band**:

| `ainStatus` | `ain` |
|---|---|
| `CERTIFIED_NEUTRAL` | >= 0.96 |
| `HIGHLY_NEUTRAL` | >= 0.90 |
| `NEUTRAL` | >= 0.80 |
| `MODERATE_BIAS` | >= 0.60 |
| `SIGNIFICANT_BIAS` | >= 0.40 |
| `HIGH_BIAS` | < 0.40 |

`status` is the **stability regime**, a different field with different
values: `STABLE` · `ACTIVE` · `INHIBITED_HIGH` · `INHIBITED_LOW`.
Plain `INHIBITED` does not exist.

### p_output — the measurement AIN is derived from

`pOutput` (`p_output` on the wire) is the engine's own reading: **output
balance, where 0.500 is equilibrium**. `ain` is computed from it, and the
computation takes an absolute value.

That has one consequence worth knowing before you build on `ain`:

```
p_output 0.4687  ->  ain 0.9373
p_output 0.5313  ->  ain 0.9373
```

**`ain` cannot tell you which side of equilibrium a reading sits on.** Two
opposite imbalances of equal size return the same AIN. If your question has
two different failure modes - too permissive vs too strict, over-represented
vs under-represented, bullish vs bearish - `ain` alone cannot answer it and
`pOutput` can:

```ts
const res = await client.compute({
  matrix: [[0, 1, 0], [1, 0, 1], [0, 1, 0]],
});
if (res.pOutput === undefined) throw new Error('engine did not return p_output');

const offset = res.pOutput - 0.5;          // signed: negative leans to 0
const side = offset > 0 ? 'toward 1' : offset < 0 ? 'toward 0' : 'balanced';
console.log(`${res.pOutput.toFixed(6)} (${side}, ${Math.abs(offset).toFixed(6)} from 0.500)`);
```

`pOutput` and `deviation` are optional on the response type because older
engine builds omitted them. Check for `undefined` rather than falling back to
`0` - a `pOutput` of 0 is not "missing", it is the most extreme reading the
engine can return.

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
  timeout: 65000,                       // Optional (ms, default 65000 — keep it
                                        //   above the engine's 60s sweep ceiling)
  retries: 3,                           // Optional (timeouts are never retried)
  debug: false,                         // Optional
});
```

### compute()

Run AIN computation on a single matrix.

```typescript
const result = await client.compute({
  matrix: [[0, 1, 0], [1, 0, 1], [0, 1, 0]],
  samples: 1000,                        // Optional (default: 1000; 100–50,000)
  timeout: 65000,                       // Optional (default: 65000)
});

// result: ComputeResult
// {
//   ain: 0.73,
//   status: 'STABLE',            // stability regime
//   ainStatus: 'MODERATE_BIAS',  // AIN band — a different field
//   isNeutral: false,            // taken from the band, not a threshold of our own
//   biasLevel: 'moderate',       // same band, so the two cannot disagree
//   tokensUsed: 1,
//   tokensRemaining: 999,
//   ...
// }
```

`samples` must be between 100 and 50,000: the engine clamps anything outside
that range and returns the clamped figure, so the SDK refuses rather than let
you record a sample count that never ran.

Keep `timeout` **above** the engine's own ceilings — 30s for `/compute`, 60s
for `/sweep`. The engine deducts tokens before it computes and refunds only
on a timeout it issues itself, so a client that gives up first pays for an
answer it then throws away. For the same reason a request that hits the
deadline is never retried.

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
//   tokensUsed: 5000,
//   tokensRemaining: 45000,
//   tokensQuota: 50000,
//   bonusBalance: 0,
//   percentUsed: 10,
//   maxDimension: 25,
//   source: 'engine_log',
//   usageMeasured: true,
//   engineUnreachable: false,
//   retrievedAt: Date,
// }
```

**Check `usageMeasured` before displaying the numbers.** Three different
server-side failures produce `tokensUsed: 0`, which is also what an idle
account produces, so the server reports how it obtained the figure —
`engine_log` (read from the engine), `engine_user_not_found`, or
`user_table_fallback`. Only the first is a measurement. Your quota is
enforced by the engine on every request regardless of what this endpoint
managed to read, so an unmeasured zero is the only warning you get before a
request is refused.

```typescript
if (!usage.usageMeasured) {
  console.warn(`usage unknown (source=${usage.source}) — showing quota only`);
}
```

### getPlans()

List all available plans and pricing. These are the fields `GET /plans`
returns; there is no daily limit and no feature list in the response.

```typescript
const plans = await client.getPlans();

// {
//   plans: [
//     { name: 'Free',  maxDimension: 9,  tokensPerMonth: 5000,  maxKeys: 1, priceUsd: 0,  unlimited: false },
//     { name: 'Basic', maxDimension: 16, tokensPerMonth: 10000, maxKeys: 1, priceUsd: 10, unlimited: false },
//     // ...
//   ],
//   fetchedAt: Date,
// }
```

`unlimited` is the engine's flag for any plan at or above 50,000,000 tokens
per month — today Enterprise XL alone, whose cap is exactly that figure. It
is not an absence of a limit; `tokensPerMonth` is what is enforced.

### getHealth()

Check that the engine is answering.

```typescript
const health = await client.getHealth();

// {
//   status: 'ok',        // the engine sends no other value
//   version: '3.2.0',
//   uptimeSeconds: 4212, // since the engine process started
// }
```

There is no uptime percentage, latency or error rate on this endpoint — the
engine does not measure them. A `getHealth()` call that resolves at all is
the availability signal.

## Utility Functions

### pricesToMatrix()

Convert price array to binary matrix.

```typescript
import { pricesToMatrix } from '@zeropointlogic/sdk';

// `prices.length` must be GREATER than `window`, and a square window x window
// matrix needs exactly 2 * window prices. 40 prices at window 20 → a 20x20.
const prices = Array.from({ length: 40 }, (_, i) => 100 + Math.sin(i / 3));
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
// "Neutral. Balanced within the engine's neutral band."
console.log(interpretAIN(0.73));
// "Moderate bias. A noticeable imbalance the engine reports as bias, not neutrality."
```

The wording and the boundaries are the engine's six `ain_status` bands, word
for word identical to the Python SDK, so the same reading never reads
differently depending on which language a team uses.

### ainToBiasLevel()

Convert an AIN score to a bias classification, on the engine's own band
boundaries.

```typescript
import { ainToBiasLevel, ainStatusToBiasLevel } from '@zeropointlogic/sdk';

ainToBiasLevel(0.92); // 'none'      — CERTIFIED_NEUTRAL / HIGHLY_NEUTRAL
ainToBiasLevel(0.85); // 'low'       — NEUTRAL
ainToBiasLevel(0.72); // 'moderate'  — MODERATE_BIAS
ainToBiasLevel(0.55); // 'high'      — SIGNIFICANT_BIAS
ainToBiasLevel(0.20); // 'critical'  — HIGH_BIAS

// When you hold the engine's band, derive from it instead — it is the
// engine's own verdict on that reading, and cannot round across a boundary.
ainStatusToBiasLevel('MODERATE_BIAS'); // 'moderate'
```

The `none`/`low` labels cover the engine's three neutral bands and
`moderate`/`high`/`critical` its three bias bands, so the split between them
is the engine's NEUTRAL floor of 0.80.

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

// `isNeutral` is the engine's own band, not a threshold picked here.
if (result.isNeutral) {
  console.log('Balanced behaviour within the engine\'s neutral band');
} else {
  console.log(`Imbalance: ${result.ainStatus}`);
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

    // 40 prices for the default window of 20 → a 20x20 matrix. Fewer than
    // `window + 1` prices makes pricesToMatrix throw a ZPLValidationError.
    const prices = Array.from({ length: 40 }, (_, i) => 100 + Math.sin(i / 3));
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
- **Timeout management** (65s default; a request that hits the deadline is not
  retried — see `compute()` above for why)

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
Reduce matrix size / samples, or raise `timeout` — never lower it. The default
is already 65000; 60000 would put your deadline *below* the engine's 60s
`/sweep` ceiling, which is how a caller ends up paying for a computation it
then abandons.

```typescript
const client = new ZPLClient({
  apiKey: 'zpl_xxx',
  timeout: 120000, // 120 seconds — above the engine's own ceilings
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
