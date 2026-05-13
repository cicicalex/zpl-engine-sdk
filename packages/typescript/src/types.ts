/**
 * Zero Point Logic Engine API Types
 * @module types
 */

/**
 * AI Neutrality Index Status - describes the bias level of the analyzed data
 */
export type AINStatus =
  | 'CERTIFIED_NEUTRAL'
  | 'STABLE'
  | 'MODERATE_BIAS'
  | 'HIGH_BIAS'
  | 'CRITICAL_BIAS';

/**
 * Bias level classification - derived from AIN value
 */
export type BiasLevel = 'none' | 'low' | 'moderate' | 'high' | 'critical';

/**
 * Binary matrix for stability analysis
 */
export type BinaryMatrix = number[][];

/**
 * Main result from ZPL Engine compute endpoint.
 *
 * AUDIT 2026-05-13 (BUG B2 — IP LEAK): pre-fix this interface
 * exposed `pOutput: number` and `deviation: number` as public,
 * documented fields. The MCP server intentionally hides those
 * (see `mcp/src/index.ts` "IP protection: expose AIN score +
 * status only"). The SDK contradicting that policy meant the
 * internal probability + deviation scalars shipped in every
 * `dist/types.d.ts` and were available to anyone running
 * `tsc` against the public types. Per the "Live Engine Only"
 * rule + the trade-secret strategy, both fields are removed
 * from the public surface. They're still in the wire response
 * but the SDK normaliser drops them before returning to the
 * caller (see `utils.ts::normalizeEngineComputeResult`).
 */
export interface ComputeResult {
  /** AI Neutrality Index: 0-1 score (1 = perfectly neutral) */
  ain: number;

  /** Categorical status of neutrality */
  status: AINStatus;

  /** Engine AIN band label (when present on API) */
  ainStatus?: string;

  /** Server-side compute time in ms (when returned by API) */
  computeMs?: number;

  /** Tokens consumed for this computation */
  tokensUsed: number;

  /**
   * Tokens remaining when the engine returns quota hints.
   *
   * AUDIT 2026-05-13 (D4): made optional. Pre-fix this was `number`
   * and defaulted to 0 when absent, which scared every fresh user
   * with "tokens=0 left" on their first compute even though they
   * had 50M left. Now `undefined` means "engine didn't tell us;
   * call getUsage() for live quota". `__str__` / display logic
   * should show "n/a" when missing, not zero.
   */
  tokensRemaining?: number;

  /** Computed: true if ain >= 0.7 (high neutrality) */
  isNeutral: boolean;

  /** Computed: bias level derived from AIN value */
  biasLevel: BiasLevel;
}

/**
 * Batch compute result - multiple matrix analyses
 */
export interface BatchComputeResult {
  results: ComputeResult[];
  totalTokensUsed: number;
  totalTokensRemaining: number;
  completedAt: Date;
}

/**
 * User account usage statistics
 */
export interface Usage {
  /** Current plan tier */
  plan: string;

  /** Daily token limit */
  dailyLimit: number;

  /** Monthly token limit */
  monthlyLimit: number;

  /** Tokens used today */
  usedToday: number;

  /** Tokens used this month */
  usedThisMonth: number;

  /** Tokens remaining in daily limit */
  tokensRemainingToday: number;

  /** Tokens remaining in monthly limit */
  tokensRemainingMonth: number;

  /** Reset time for daily quota (ISO 8601) */
  resetAtToday: string;

  /** Reset time for monthly quota (ISO 8601) */
  resetAtMonth: string;
}

/**
 * Available plans and their details
 */
export interface Plan {
  /** Plan identifier: free, basic, pro, gamepro, studio, agent, enterprise, xl */
  id: string;

  /** User-friendly name */
  name: string;

  /** Monthly price in USD */
  price: number;

  /** Daily token limit */
  dailyLimit: number;

  /** Monthly token limit */
  monthlyLimit: number;

  /** List of features included */
  features: string[];
}

/**
 * Plans catalog
 */
export interface PlansResponse {
  plans: Plan[];
  fetchedAt: Date;
}

/**
 * Health check response from /health endpoint
 */
export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  uptime: number;
  version: string;
  timestamp: string;
}

/**
 * Request options for compute operations
 */
export interface ComputeOptions {
  /** Number of samples for statistical analysis (default: 1000) */
  samples?: number;

  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;

  /** API key override (uses client default if not provided) */
  apiKey?: string;

  /** Enable debug logging */
  debug?: boolean;
}

/**
 * Batch compute options
 */
export interface BatchComputeOptions extends ComputeOptions {
  /** Stop on first error (default: false) */
  stopOnError?: boolean;

  /** Concurrent requests (default: 3) */
  concurrency?: number;
}

/**
 * Client configuration
 */
export interface ZPLClientConfig {
  /** API key for authentication */
  apiKey: string;

  /** Base URL of ZPL Engine (default: https://engine.zeropointlogic.io) */
  baseUrl?: string;

  /** Default timeout in milliseconds (default: 30000) */
  timeout?: number;

  /** Number of retries for failed requests (default: 3) */
  retries?: number;

  /** Enable debug logging (default: false) */
  debug?: boolean;

  /** Custom User-Agent header (default: auto-generated) */
  userAgent?: string;

  /**
   * ADR 0002 `X-ZPL-Client` (default: `sdk-typescript`).
   * Override only for forks or internal bridges.
   */
  xZplClient?: string;

  /** ADR 0002 `X-ZPL-Client-Version` (default: package semver). */
  xZplClientVersion?: string;

  /** Fetch implementation override (for Node.js compatibility) */
  fetch?: typeof globalThis.fetch;
}

/**
 * Retry policy configuration
 */
export interface RetryPolicy {
  maxRetries: number;
  initialDelayMs: number;
  maxDelayMs: number;
  backoffMultiplier: number;
}

/**
 * Request metadata for logging/debugging
 */
export interface RequestMetadata {
  requestId: string;
  timestamp: Date;
  endpoint: string;
  method: 'GET' | 'POST';
  retryCount: number;
}

/**
 * Compute request payload
 */
export interface ComputeRequest {
  /** Binary matrix (N×N where each element is 0 or 1) */
  matrix: BinaryMatrix;

  /** Number of samples for analysis */
  samples: number;

  /** Optional API key override */
  api_key?: string;
}

/**
 * Error response from API
 */
export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    status: number;
    details?: Record<string, unknown>;
  };
}
