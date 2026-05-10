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
  ComputeRequest,
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

    this.apiKey = config.apiKey.trim();
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

    const payload: ComputeRequest = {
      matrix,
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
              totalTokensRemaining = result.tokensRemaining;
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
