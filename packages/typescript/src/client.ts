/**
 * ZPL Engine API Client
 * @module client
 */

import type {
  ZPLClientConfig,
  ComputeResult,
  BatchComputeResult,
  BatchComputeOptions,
  Usage,
  PlansResponse,
  HealthResponse,
  BinaryMatrix,
  RetryPolicy,
} from './types.js';

import {
  ZPLError,
  ZPLAuthError,
  ZPLRateLimitError,
  ZPLQuotaExceededError,
  ZPLValidationError,
  ZPLTimeoutError,
  ZPLNetworkError,
  parseApiError,
  parseEngineHttpError,
} from './errors.js';

import {
  generateRequestId,
  calculateBackoffDelay,
  isRetryableStatus,
  validateMatrix,
  sleep,
  normalizeEngineComputeResult,
} from './utils.js';

import { SDK_VERSION, ZPL_SDK_CLIENT_TYPE } from './meta.js';

/**
 * ZPL Engine API Client
 * Provides methods to interact with the ZPL stability/neutrality analysis engine
 *
 * @example
 * ```typescript
 * const client = new ZPLClient({ apiKey: 'zpl_xxx' });
 *
 * const result = await client.compute({
 *   matrix: [[0,1],[1,0]],
 *   samples: 1000,
 * });
 *
 * console.log(result.ain);     // 0.73
 * console.log(result.status);  // 'STABLE'
 * ```
 */
export class ZPLClient {
  private apiKey: string;
  private baseUrl: string;
  private timeout: number;
  private retryPolicy: RetryPolicy;
  private debug: boolean;
  private userAgent: string;
  private zplClientType: string;
  private zplClientVersion: string;
  private fetchFn: typeof globalThis.fetch;

  constructor(config: ZPLClientConfig) {
    if (!config.apiKey || config.apiKey.trim() === '') {
      throw new ZPLValidationError('API key is required');
    }

    const trimmed = config.apiKey.trim();

    // v2.0.2 (audit 2026-05-13): reject service keys outright. Pre-2.0.2
    // the SDK accepted any non-empty string, so a developer could
    // accidentally paste a `zpl_s_*` server-only key into client-side
    // browser code and ship the secret. CLI and MCP already enforce
    // this regex; SDK is now consistent.
    //
    // Format: `zpl_u_<48 hex>` or `zpl_u_<prefix>_<48 hex>` for
    // wizard-issued user keys (mcp, cli). Anything else is rejected.
    if (/^zpl_s_/i.test(trimmed)) {
      throw new ZPLValidationError(
        'apiKey is a service key (zpl_s_*). Service keys are server-only — never ship them in client bundles. Use a user key (zpl_u_*) from `zpl login` or zeropointlogic.io/dashboard/api-keys.',
      );
    }
    if (!/^zpl_u_(?:[a-z]+_)?[a-f0-9]{48}$/.test(trimmed)) {
      throw new ZPLValidationError(
        'apiKey does not match the expected format (zpl_u_<48 hex> or zpl_u_<prefix>_<48 hex>). Check for trailing whitespace or stray characters.',
      );
    }

    this.apiKey = trimmed;
    this.baseUrl = (config.baseUrl || 'https://engine.zeropointlogic.io').replace(/\/$/, '');
    this.timeout = config.timeout || 30000;
    this.debug = config.debug || false;

    this.retryPolicy = {
      maxRetries: config.retries ?? 3,
      initialDelayMs: 100,
      maxDelayMs: 10000,
      backoffMultiplier: 2,
    };

    this.userAgent =
      config.userAgent ||
      `Mozilla/5.0 (compatible; @zeropointlogic/sdk/${SDK_VERSION}; +https://zeropointlogic.io)`;

    this.zplClientType = config.xZplClient ?? ZPL_SDK_CLIENT_TYPE;
    this.zplClientVersion = config.xZplClientVersion ?? SDK_VERSION;

    // Use provided fetch or globalThis.fetch (works in Node.js 18+ and browsers)
    this.fetchFn = config.fetch || globalThis.fetch;

    // v2.0.2 (audit 2026-05-13 Gap J): fire a one-shot heartbeat to ZPL Main
    // so the funnel dashboard counts SDK adoption. Receiver already
    // whitelists `sdk-typescript`. Fire-and-forget — never blocks the
    // happy path; never throws. Set process.env.ZPL_SKIP_HEARTBEAT=1 to
    // disable (CI runners that don't want the network call).
    this.sendHeartbeatOnce();
  }

  /** Per-process dedup so 100 ZPLClient() in a loop = 1 heartbeat. */
  private static heartbeatSent = false;
  private sendHeartbeatOnce(): void {
    if (ZPLClient.heartbeatSent) return;
    if (typeof process !== 'undefined' && process.env?.ZPL_SKIP_HEARTBEAT === '1') return;
    ZPLClient.heartbeatSent = true;
    const url =
      (typeof process !== 'undefined' && process.env?.ZPL_HEARTBEAT_URL) ||
      'https://zeropointlogic.io/api/auth/cli/heartbeat';
    // Use AbortSignal.timeout if available (Node 18.17+ / modern browsers).
    const controller = typeof AbortController !== 'undefined' ? new AbortController() : undefined;
    const timer = controller
      ? setTimeout(() => controller.abort(), 5_000)
      : undefined;
    this.fetchFn(url, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
        'User-Agent': this.userAgent,
      },
      body: JSON.stringify({
        client: this.zplClientType,
        version: this.zplClientVersion,
      }),
      signal: controller?.signal,
    })
      .catch(() => {
        /* fire-and-forget — never throw */
      })
      .finally(() => {
        if (timer) clearTimeout(timer);
      });
  }

  /**
   * Run AIN (AI Neutrality Index) computation on a binary matrix
   *
   * @param options - Computation options including matrix and samples count
   * @returns ComputeResult with AIN, status, and token usage
   * @throws {ZPLAuthError} if API key is invalid
   * @throws {ZPLRateLimitError} if rate limited
   * @throws {ZPLQuotaExceededError} if token quota exceeded
   * @throws {ZPLError} on other API errors
   *
   * @example
   * ```typescript
   * const result = await client.compute({
   *   matrix: [[0, 1, 0], [1, 0, 1], [0, 1, 0]],
   *   samples: 500,
   * });
   * ```
   */
  async compute(options: {
    matrix: BinaryMatrix;
    samples?: number;
    timeout?: number;
    apiKey?: string;
  }): Promise<ComputeResult> {
    const { matrix, samples = 1000, timeout, apiKey } = options;

    // Validate matrix
    try {
      validateMatrix(matrix);
    } catch (error) {
      if (error instanceof ZPLValidationError) {
        throw error;
      }
      throw new ZPLValidationError(
        `Invalid matrix: ${error instanceof Error ? error.message : 'unknown error'}`
      );
    }

    // Validate samples
    if (!Number.isInteger(samples) || samples < 1 || samples > 1000000) {
      throw new ZPLValidationError(
        'Samples must be an integer between 1 and 1,000,000'
      );
    }

    // v2.0 — convert (matrix, samples) to the engine's actual wire shape
    // (d, bias, samples). v1.x sent {matrix, samples} which the Rust engine
    // never accepted: every call returned 400 "Failed to deserialize: missing
    // field `bias`". The SDK had zero working users before v2.0 because of it.
    //
    // d = number of rows (matrix is N×N per the validateMatrix contract).
    // bias = density of 1s across the matrix (sum / total cells). This is
    // the most natural interpretation of "bias" for a binary input — all 0s
    // means no positive class (0.0 bias), all 1s means full positive class
    // (1.0 bias), a balanced 50/50 matrix means 0.5. The engine treats bias
    // as the probability parameter of the binary input distribution.
    const d = matrix.length;
    let ones = 0;
    for (const row of matrix) {
      for (const cell of row) {
        if (cell === 1) ones += 1;
      }
    }
    const total = d * d;
    const bias = total > 0 ? ones / total : 0;

    const payload: Record<string, unknown> = {
      d,
      bias,
      samples,
    };

    // Add optional API key override to payload
    if (apiKey) {
      payload.api_key = apiKey;
    }

    const raw = await this._request<Record<string, unknown>>(
      '/compute',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      { timeout }
    );

    const core = normalizeEngineComputeResult(raw);
    const result: ComputeResult = {
      ...core,
      isNeutral: core.ain >= 0.7,
      biasLevel: this._ainToBiasLevel(core.ain),
    };

    return result;
  }

  /**
   * Run multiple AIN computations in parallel
   *
   * @param matrices - Array of binary matrices to analyze
   * @param options - Batch options (samples, concurrency, etc.)
   * @returns BatchComputeResult with all results and aggregated stats
   *
   * @example
   * ```typescript
   * const results = await client.batchCompute(
   *   [matrix1, matrix2, matrix3],
   *   { samples: 500, concurrency: 2 }
   * );
   * ```
   */
  async batchCompute(
    matrices: BinaryMatrix[],
    options: BatchComputeOptions = {}
  ): Promise<BatchComputeResult> {
    const {
      samples = 1000,
      timeout,
      stopOnError = false,
      concurrency = 3,
      apiKey,
    } = options;

    if (!Array.isArray(matrices) || matrices.length === 0) {
      throw new ZPLValidationError('Matrices array must be non-empty');
    }

    if (!Number.isInteger(concurrency) || concurrency < 1) {
      throw new ZPLValidationError('Concurrency must be a positive integer');
    }

    const results: ComputeResult[] = [];
    const errors: Error[] = [];
    let totalTokensUsed = 0;
    let totalTokensRemaining = 0;

    // Process matrices with concurrency control
    const queue = [...matrices];
    const workers: Promise<void>[] = [];

    for (let i = 0; i < concurrency; i++) {
      workers.push(
        (async () => {
          while (queue.length > 0) {
            const matrix = queue.shift();
            if (!matrix) break;

            try {
              const result = await this.compute({
                matrix,
                samples,
                timeout,
                apiKey,
              });

              results.push(result);
              totalTokensUsed += result.tokensUsed;
              // AUDIT 2026-05-13 (D4): tokensRemaining is now Optional —
              // only update the running total when the engine actually
              // emitted a value.
              if (result.tokensRemaining !== undefined) {
                totalTokensRemaining = result.tokensRemaining;
              }
            } catch (error) {
              errors.push(error instanceof Error ? error : new Error(String(error)));

              if (stopOnError) {
                queue.length = 0; // Clear queue to stop processing
              }
            }
          }
        })()
      );
    }

    // Wait for all workers
    await Promise.all(workers);

    if (errors.length > 0 && stopOnError) {
      throw errors[0];
    }

    return {
      results,
      totalTokensUsed,
      totalTokensRemaining,
      completedAt: new Date(),
    };
  }

  /**
   * Get current usage and quota information
   *
   * @param timeout - Optional timeout override
   * @returns Usage object with current plan and token usage
   * @throws {ZPLError} on API error
   */
  async getUsage(timeout?: number): Promise<Usage> {
    return this._request<Usage>('/usage', { method: 'GET' }, { timeout });
  }

  /**
   * Get available plans and pricing
   *
   * @param timeout - Optional timeout override
   * @returns PlansResponse with all available plans
   * @throws {ZPLError} on API error
   */
  async getPlans(timeout?: number): Promise<PlansResponse> {
    const response = await this._request<{ plans: any[] }>(
      '/plans',
      { method: 'GET' },
      { timeout }
    );

    return {
      plans: response.plans,
      fetchedAt: new Date(),
    };
  }

  /**
   * Check API health and status
   *
   * @param timeout - Optional timeout override
   * @returns HealthResponse with service status
   * @throws {ZPLError} on API error
   */
  async getHealth(timeout?: number): Promise<HealthResponse> {
    return this._request<HealthResponse>('/health', { method: 'GET' }, { timeout });
  }

  /**
   * Private method to make HTTP requests with retry logic
   */
  private async _request<T>(
    endpoint: string,
    init: RequestInit,
    options: { timeout?: number } = {}
  ): Promise<T> {
    const requestTimeout = options.timeout || this.timeout;
    const url = `${this.baseUrl}${endpoint}`;
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.retryPolicy.maxRetries; attempt++) {
      try {
        const response = await this._fetchWithTimeout(
          url,
          {
            ...init,
            headers: {
              'Content-Type': 'application/json',
              'User-Agent': this.userAgent,
              'X-ZPL-Client': this.zplClientType,
              'X-ZPL-Client-Version': this.zplClientVersion,
              'X-API-Key': this.apiKey,
              Authorization: `Bearer ${this.apiKey}`,
              'X-Request-ID': generateRequestId(),
              ...init.headers,
            },
          },
          requestTimeout
        );

        // Handle successful response
        if (response.ok) {
          const data = (await response.json()) as T;
          return data;
        }

        // Handle error responses
        const ct = response.headers.get('content-type') ?? '';
        if (!ct.includes('application/json')) {
          const msg = await parseEngineHttpError(response);
          const errorData = { message: msg };
          if (isRetryableStatus(response.status) && attempt < this.retryPolicy.maxRetries) {
            const delayMs = calculateBackoffDelay(
              attempt,
              this.retryPolicy.initialDelayMs,
              this.retryPolicy.maxDelayMs,
              this.retryPolicy.backoffMultiplier
            );
            if (this.debug) {
              console.debug(
                `[ZPL] Retry attempt ${attempt + 1}/${this.retryPolicy.maxRetries} after ${delayMs}ms`
              );
            }
            await sleep(delayMs);
            continue;
          }
          throw parseApiError(response.status, errorData);
        }

        const errorData = await this._parseErrorResponse(response);

        // Determine if we should retry
        if (isRetryableStatus(response.status) && attempt < this.retryPolicy.maxRetries) {
          const delayMs = calculateBackoffDelay(
            attempt,
            this.retryPolicy.initialDelayMs,
            this.retryPolicy.maxDelayMs,
            this.retryPolicy.backoffMultiplier
          );

          if (this.debug) {
            console.debug(
              `[ZPL] Retry attempt ${attempt + 1}/${this.retryPolicy.maxRetries} after ${delayMs}ms`
            );
          }

          await sleep(delayMs);
          continue;
        }

        // Non-retryable error
        throw parseApiError(response.status, errorData);
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        // Don't retry on client errors (400-499) except 408 and 429
        if (
          error instanceof ZPLAuthError ||
          error instanceof ZPLValidationError ||
          error instanceof ZPLQuotaExceededError
        ) {
          throw error;
        }

        // Retry on network errors
        if (attempt < this.retryPolicy.maxRetries && isRetryableError(error)) {
          const delayMs = calculateBackoffDelay(
            attempt,
            this.retryPolicy.initialDelayMs,
            this.retryPolicy.maxDelayMs,
            this.retryPolicy.backoffMultiplier
          );

          if (this.debug) {
            console.debug(
              `[ZPL] Network retry attempt ${attempt + 1}/${this.retryPolicy.maxRetries} after ${delayMs}ms`
            );
          }

          await sleep(delayMs);
          continue;
        }

        throw error;
      }
    }

    // All retries exhausted
    throw lastError || new ZPLError('Request failed after all retries');
  }

  /**
   * Fetch with timeout support
   */
  private async _fetchWithTimeout(
    url: string,
    init: RequestInit,
    timeoutMs: number
  ): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await this.fetchFn(url, {
        ...init,
        signal: controller.signal,
      });

      return response;
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw new ZPLTimeoutError(
          `Request timeout after ${timeoutMs}ms`,
          timeoutMs
        );
      }

      throw new ZPLNetworkError(
        `Network error: ${error instanceof Error ? error.message : 'unknown'}`,
        error instanceof Error ? error : undefined
      );
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Parse error response from API
   */
  private async _parseErrorResponse(
    response: Response
  ): Promise<Record<string, unknown> | null> {
    try {
      const contentType = response.headers.get('content-type');

      if (contentType?.includes('application/json')) {
        return (await response.json()) as Record<string, unknown>;
      }

      return null;
    } catch {
      return null;
    }
  }

  /**
   * Convert AIN score to bias level
   */
  private _ainToBiasLevel(
    ain: number
  ): 'none' | 'low' | 'moderate' | 'high' | 'critical' {
    if (ain >= 0.8) return 'none';
    if (ain >= 0.7) return 'low';
    if (ain >= 0.5) return 'moderate';
    if (ain >= 0.3) return 'high';
    return 'critical';
  }
}

/**
 * Check if an error is retryable
 */
function isRetryableError(error: unknown): boolean {
  if (error instanceof ZPLTimeoutError || error instanceof ZPLNetworkError) {
    return true;
  }

  if (error instanceof ZPLRateLimitError) {
    return true;
  }

  return false;
}
