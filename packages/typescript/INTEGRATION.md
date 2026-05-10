# Integration Guide for ZPL TypeScript SDK

Quick patterns for integrating ZPL SDK into your projects.

## Installation

```bash
npm install @zeropointlogic/sdk
```

## Node.js Backend Integration

### Express.js Endpoint

```typescript
import express from 'express';
import { ZPLClient, pricesToMatrix } from '@zeropointlogic/sdk';

const app = express();
const client = new ZPLClient({
  apiKey: process.env.ZPL_API_KEY,
});

app.post('/api/analyze', async (req, res) => {
  try {
    const { prices } = req.body;
    const matrix = pricesToMatrix(prices, 20);

    const result = await client.compute({
      matrix,
      samples: 1000,
    });

    res.json({
      ain: result.ain,
      status: result.status,
      isNeutral: result.isNeutral,
    });
  } catch (error) {
    if (error instanceof ZPLQuotaExceededError) {
      res.status(402).json({ error: 'Quota exceeded' });
    } else {
      res.status(500).json({ error: 'Analysis failed' });
    }
  }
});
```

### Next.js API Route

```typescript
// app/api/analyze/route.ts
import { ZPLClient, pricesToMatrix } from '@zeropointlogic/sdk';
import { NextRequest, NextResponse } from 'next/server';

const client = new ZPLClient({
  apiKey: process.env.ZPL_API_KEY,
});

export async function POST(request: NextRequest) {
  try {
    const { prices } = await request.json();
    const matrix = pricesToMatrix(prices);

    const result = await client.compute({
      matrix,
      samples: 1000,
    });

    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
```

### Fastify

```typescript
import Fastify from 'fastify';
import { ZPLClient } from '@zeropointlogic/sdk';

const fastify = Fastify();
const client = new ZPLClient({
  apiKey: process.env.ZPL_API_KEY,
});

fastify.post('/analyze', async (request, reply) => {
  const { matrix, samples } = request.body as {
    matrix: number[][];
    samples: number;
  };

  const result = await client.compute({ matrix, samples });
  return reply.send(result);
});
```

## React Frontend Integration

### React Hook

```typescript
// hooks/useZPLAnalysis.ts
import { useState, useCallback } from 'react';
import { ZPLClient, type ComputeResult } from '@zeropointlogic/sdk';

const client = new ZPLClient({
  apiKey: process.env.REACT_APP_ZPL_API_KEY,
});

export function useZPLAnalysis() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ComputeResult | null>(null);

  const analyze = useCallback(
    async (matrix: number[][], samples = 1000) => {
      setLoading(true);
      setError(null);

      try {
        const res = await client.compute({ matrix, samples });
        setResult(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Analysis failed');
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return { analyze, loading, error, result };
}
```

### React Component

```typescript
// components/BiasAnalyzer.tsx
import React from 'react';
import { useZPLAnalysis } from '../hooks/useZPLAnalysis';
import { pricesToMatrix } from '@zeropointlogic/sdk';

export function BiasAnalyzer() {
  const { analyze, loading, error, result } = useZPLAnalysis();
  const [prices, setPrices] = React.useState<string>('');

  const handleAnalyze = async () => {
    const priceArray = prices
      .split(',')
      .map((p) => parseFloat(p))
      .filter(Boolean);

    if (priceArray.length < 2) {
      alert('Enter at least 2 prices');
      return;
    }

    const matrix = pricesToMatrix(priceArray);
    await analyze(matrix, 1000);
  };

  return (
    <div>
      <textarea
        value={prices}
        onChange={(e) => setPrices(e.target.value)}
        placeholder="100, 102, 101, 103..."
      />
      <button onClick={handleAnalyze} disabled={loading}>
        {loading ? 'Analyzing...' : 'Analyze'}
      </button>

      {error && <p style={{ color: 'red' }}>{error}</p>}
      {result && (
        <div>
          <p>AIN: {result.ain.toFixed(4)}</p>
          <p>Status: {result.status}</p>
          <p>Neutral: {result.isNeutral ? 'Yes' : 'No'}</p>
        </div>
      )}
    </div>
  );
}
```

## Vue.js Integration

### Vue 3 Composable

```typescript
// composables/useZPL.ts
import { ref } from 'vue';
import { ZPLClient, type ComputeResult } from '@zeropointlogic/sdk';

const client = new ZPLClient({
  apiKey: import.meta.env.VITE_ZPL_API_KEY,
});

export function useZPL() {
  const loading = ref(false);
  const error = ref<string | null>(null);
  const result = ref<ComputeResult | null>(null);

  const compute = async (matrix: number[][], samples = 1000) => {
    loading.value = true;
    error.value = null;

    try {
      result.value = await client.compute({ matrix, samples });
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed';
    } finally {
      loading.value = false;
    }
  };

  return { loading, error, result, compute };
}
```

## Svelte Integration

```svelte
<!-- components/ZPLAnalyzer.svelte -->
<script lang="ts">
  import { ZPLClient, createRandomMatrix } from '@zeropointlogic/sdk';

  const client = new ZPLClient({
    apiKey: import.meta.env.VITE_ZPL_API_KEY,
  });

  let loading = false;
  let result = null;
  let error = '';

  async function analyze() {
    loading = true;
    error = '';

    try {
      const matrix = createRandomMatrix(16);
      result = await client.compute({ matrix, samples: 1000 });
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed';
    } finally {
      loading = false;
    }
  }
</script>

<div>
  <button on:click={analyze} disabled={loading}>
    {loading ? 'Analyzing...' : 'Analyze'}
  </button>

  {#if error}
    <p style="color: red;">{error}</p>
  {/if}

  {#if result}
    <p>AIN: {result.ain.toFixed(4)}</p>
    <p>Status: {result.status}</p>
  {/if}
</div>
```

## Data Pipeline Integration

### Node.js Worker

```typescript
// worker.ts - Process matrices in background
import { ZPLClient } from '@zeropointlogic/sdk';
import { parentPort } from 'worker_threads';

const client = new ZPLClient({
  apiKey: process.env.ZPL_API_KEY,
});

parentPort?.on('message', async (matrix) => {
  try {
    const result = await client.compute({ matrix, samples: 5000 });
    parentPort?.postMessage({ success: true, result });
  } catch (error) {
    parentPort?.postMessage({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    });
  }
});
```

### Streaming Results

```typescript
// Stream large batch results
import { ZPLClient } from '@zeropointlogic/sdk';

const client = new ZPLClient({
  apiKey: process.env.ZPL_API_KEY,
});

async function* analyzeMatrices(matrices: number[][][]) {
  for (const matrix of matrices) {
    try {
      const result = await client.compute({
        matrix,
        samples: 1000,
      });
      yield { status: 'success', result };
    } catch (error) {
      yield { status: 'error', error };
    }
  }
}

// Usage
for await (const item of analyzeMatrices(matricesList)) {
  console.log(item);
}
```

## Error Handling Patterns

### Circuit Breaker

```typescript
import { ZPLClient, ZPLRateLimitError } from '@zeropointlogic/sdk';

class CircuitBreaker {
  private failures = 0;
  private state: 'closed' | 'open' | 'half-open' = 'closed';
  private nextRetry = 0;

  constructor(
    private client: ZPLClient,
    private failureThreshold = 5,
    private resetTimeout = 60000
  ) {}

  async compute(matrix: number[][], samples: number) {
    if (this.state === 'open') {
      if (Date.now() < this.nextRetry) {
        throw new Error('Circuit breaker is open');
      }
      this.state = 'half-open';
    }

    try {
      const result = await this.client.compute({ matrix, samples });
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure(error);
      throw error;
    }
  }

  private onSuccess() {
    this.failures = 0;
    this.state = 'closed';
  }

  private onFailure(error: unknown) {
    if (error instanceof ZPLRateLimitError) {
      this.failures++;
      if (this.failures >= this.failureThreshold) {
        this.state = 'open';
        this.nextRetry = Date.now() + this.resetTimeout;
      }
    }
  }
}
```

### Retry with Exponential Backoff

```typescript
import { ZPLClient } from '@zeropointlogic/sdk';

async function withRetry(
  client: ZPLClient,
  matrix: number[][],
  maxRetries = 3
) {
  let lastError;

  for (let i = 0; i < maxRetries; i++) {
    try {
      return await client.compute({ matrix, samples: 1000 });
    } catch (error) {
      lastError = error;

      if (i < maxRetries - 1) {
        const delay = Math.pow(2, i) * 100; // 100ms, 200ms, 400ms
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError;
}
```

## Caching Results

```typescript
import { ZPLClient, type ComputeResult } from '@zeropointlogic/sdk';

class CachedClient {
  private cache = new Map<string, ComputeResult>();

  constructor(private client: ZPLClient) {}

  async compute(matrix: number[][], samples: number) {
    const key = `${JSON.stringify(matrix)}_${samples}`;

    if (this.cache.has(key)) {
      return this.cache.get(key)!;
    }

    const result = await this.client.compute({ matrix, samples });
    this.cache.set(key, result);

    return result;
  }

  clearCache() {
    this.cache.clear();
  }
}
```

## Monitoring & Logging

```typescript
import { ZPLClient } from '@zeropointlogic/sdk';

class MonitoredClient extends ZPLClient {
  private metrics = {
    totalRequests: 0,
    successfulRequests: 0,
    failedRequests: 0,
    totalTokensUsed: 0,
    startTime: Date.now(),
  };

  async compute(options: Parameters<ZPLClient['compute']>[0]) {
    this.metrics.totalRequests++;

    try {
      const result = await super.compute(options);
      this.metrics.successfulRequests++;
      this.metrics.totalTokensUsed += result.tokensUsed;
      return result;
    } catch (error) {
      this.metrics.failedRequests++;
      throw error;
    }
  }

  getMetrics() {
    return {
      ...this.metrics,
      successRate:
        (this.metrics.successfulRequests / this.metrics.totalRequests) * 100,
      uptime: Date.now() - this.metrics.startTime,
    };
  }
}
```

## Testing

### Jest Test Example

```typescript
import { ZPLClient, createRandomMatrix } from '@zeropointlogic/sdk';

describe('ZPL Analysis', () => {
  let client: ZPLClient;

  beforeAll(() => {
    client = new ZPLClient({
      apiKey: process.env.ZPL_TEST_KEY || 'test_key',
    });
  });

  test('should compute AIN for random matrix', async () => {
    const matrix = createRandomMatrix(8);
    const result = await client.compute({
      matrix,
      samples: 100,
    });

    expect(result.ain).toBeGreaterThanOrEqual(0);
    expect(result.ain).toBeLessThanOrEqual(1);
    expect(result.status).toBeDefined();
  });

  test('should handle invalid matrix', async () => {
    expect(async () => {
      await client.compute({
        matrix: [[1, 2], [3, 4]],
        samples: 100,
      });
    }).rejects.toThrow();
  });
});
```

## Environment Setup

```bash
# .env.local
REACT_APP_ZPL_API_KEY=zpl_xxx

# .env
ZPL_API_KEY=zpl_xxx

# .env.test
ZPL_TEST_KEY=zpl_test_xxx
```

## Performance Tips

1. **Reuse Client Instances** - Create once, use many times
2. **Batch Processing** - Use `batchCompute()` for multiple matrices
3. **Cache Results** - Results are deterministic for same input
4. **Async/Await** - Don't block on analysis
5. **Concurrency Control** - Balance speed with rate limits
6. **Error Recovery** - Implement retries for transient failures
