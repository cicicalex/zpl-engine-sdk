# ZPL SDK - Quick Start

## 1. Install

```bash
npm install @zeropointlogic/sdk
```

## 2. Initialize Client

```typescript
import { ZPLClient } from '@zeropointlogic/sdk';

const client = new ZPLClient({
  apiKey: process.env.ZPL_API_KEY,
});
```

## 3. Analyze a Binary Matrix

```typescript
const result = await client.compute({
  matrix: [[0, 1], [1, 0]],
  samples: 1000,
});

console.log(result.ain);      // 0-1 score
console.log(result.status);   // 'STABLE', 'HIGH_BIAS', etc
console.log(result.isNeutral); // true/false
```

## 4. Common Use Cases

### Price Analysis
```typescript
import { pricesToMatrix } from '@zeropointlogic/sdk';

const prices = [100, 102, 101, 103, 105];
const matrix = pricesToMatrix(prices);
const result = await client.compute({ matrix, samples: 5000 });
```

### Random Testing
```typescript
import { createRandomMatrix } from '@zeropointlogic/sdk';

const matrix = createRandomMatrix(16); // 16x16
const result = await client.compute({ matrix });
```

### Batch Analysis
```typescript
const matrices = [matrix1, matrix2, matrix3];
const results = await client.batchCompute(matrices, {
  samples: 1000,
  concurrency: 2,
});
```

## 5. Error Handling

```typescript
import {
  ZPLAuthError,
  ZPLQuotaExceededError,
  ZPLRateLimitError,
} from '@zeropointlogic/sdk';

try {
  const result = await client.compute({ matrix, samples: 1000 });
} catch (error) {
  if (error instanceof ZPLAuthError) {
    console.error('Invalid API key');
  } else if (error instanceof ZPLQuotaExceededError) {
    console.error('Token quota exceeded');
  } else if (error instanceof ZPLRateLimitError) {
    console.error('Rate limited, retry later');
  }
}
```

## 6. Check Usage

```typescript
const usage = await client.getUsage();
console.log(usage.tokensRemainingMonth); // 9,950
```

## 7. Get Plans

```typescript
const plans = await client.getPlans();
plans.plans.forEach((plan) => {
  console.log(`${plan.name}: $${plan.price}/month`);
});
```

## Files Overview

| File | Purpose |
|------|---------|
| `src/index.ts` | Main exports |
| `src/client.ts` | ZPLClient class |
| `src/types.ts` | TypeScript types |
| `src/errors.ts` | Error classes |
| `src/utils.ts` | Utility functions |
| `examples/basic.ts` | Simple example |
| `examples/crypto-analysis.ts` | Real price analysis |
| `examples/game-economy.ts` | Batch processing |
| `README.md` | Full documentation |
| `STRUCTURE.md` | Architecture details |
| `INTEGRATION.md` | Framework examples |

## Key Features

✓ Zero dependencies  
✓ Full TypeScript  
✓ Automatic retry logic  
✓ Request timeout (30s)  
✓ Batch processing with concurrency  
✓ Tree-shakeable exports  
✓ Works in Node.js & browsers  
✓ Specific error types  

## Status Values

| Value | Meaning |
|-------|---------|
| `CERTIFIED_NEUTRAL` | AIN 0.95+ |
| `STABLE` | AIN 0.8-0.95 |
| `MODERATE_BIAS` | AIN 0.5-0.8 |
| `HIGH_BIAS` | AIN 0.3-0.5 |
| `CRITICAL_BIAS` | AIN 0-0.3 |

## Result Fields

```typescript
{
  ain: 0.73,                    // AI Neutrality Index (0-1)
  pOutput: 0.48,               // Predicted output probability
  deviation: 0.12,             // Standard deviation
  status: 'STABLE',            // Categorical status
  isNeutral: true,             // Computed: ain >= 0.7
  biasLevel: 'low',            // Computed: from ain
  tokensUsed: 1,               // Tokens consumed
  tokensRemaining: 999,        // Tokens left in quota
}
```

## Common Patterns

### With Frontend
```typescript
// React
const result = await client.compute({ matrix, samples: 1000 });
setAnalysis(result);
```

### With Backend API
```typescript
// Express
app.post('/analyze', async (req, res) => {
  const result = await client.compute({ matrix: req.body.matrix });
  res.json(result);
});
```

### Batch with Error Handling
```typescript
const batch = await client.batchCompute(matrices, {
  stopOnError: false,
}).catch(err => console.error(err));
```

## Documentation

- Full Docs: `README.md`
- Architecture: `STRUCTURE.md`
- Integration: `INTEGRATION.md`
- Examples: `examples/`

## Next Steps

1. Read `README.md` for complete API documentation
2. Check `examples/` for real-world use cases
3. Review `INTEGRATION.md` for framework-specific patterns
4. See `STRUCTURE.md` for architecture details

## Support

- GitHub: https://github.com/zeropointlogic/sdk-ts
- Email: support@zeropointlogic.io
- Docs: https://zeropointlogic.io/docs
