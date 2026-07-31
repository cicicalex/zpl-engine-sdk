/**
 * Zero Point Logic Engine API Types
 * @module types
 */

/**
 * `ain_status` — quality of the balance, derived from the `ain` value.
 *
 * These are the ONLY valid values. Bands (inclusive lower bound):
 *   CERTIFIED_NEUTRAL >= 0.96 · HIGHLY_NEUTRAL >= 0.90 · NEUTRAL >= 0.80
 *   MODERATE_BIAS >= 0.60 · SIGNIFICANT_BIAS >= 0.40 · HIGH_BIAS < 0.40
 *
 * Pre-fix this union mixed `ain_status` values with `status` values
 * (`STABLE`) and invented a `CRITICAL_BIAS` member that no engine ever
 * returns, while omitting HIGHLY_NEUTRAL / NEUTRAL / SIGNIFICANT_BIAS.
 */
export type AINStatus =
  | 'CERTIFIED_NEUTRAL'
  | 'HIGHLY_NEUTRAL'
  | 'NEUTRAL'
  | 'MODERATE_BIAS'
  | 'SIGNIFICANT_BIAS'
  | 'HIGH_BIAS';

/**
 * `status` — stability regime. A DIFFERENT field from {@link AINStatus}
 * with a different meaning; the two are never interchangeable.
 *
 * Plain `INHIBITED` does not exist — only `INHIBITED_HIGH` / `INHIBITED_LOW`.
 */
export type StabilityStatus =
  | 'STABLE'
  | 'ACTIVE'
  | 'INHIBITED_HIGH'
  | 'INHIBITED_LOW';

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
 * AUDIT 2026-05-13 (BUG B2): `pOutput` and `deviation` were removed from this
 * interface as trade-secret intermediates, to match the MCP, which hid them
 * under an "IP protection" note.
 *
 * AUDIT 2026-07-30: restored, both here and in the MCP, after checking what
 * the wire actually carries. The engine's HTTP response serialises p_output
 * and deviation to every caller holding a key, so neither was ever secret —
 * the only people they were hidden from were those reading through a client.
 * The owner's position, asked directly: the calculation stays secret, the
 * numbers it produces do not.
 *
 * They are optional because the engine may not send them, and absent is not
 * the same as zero: a pOutput of 0 would mean the output stream was entirely
 * zeros, which is a real and very different reading from "not reported".
 */
export interface ComputeResult {
  /**
   * AI Neutrality Index: float on the 0.0 – 1.0 scale, 6 decimals
   * (1.0 = perfectly neutral).
   *
   * Display as a percentage with `(ain * 100).toFixed(2)`. Never
   * `Math.round(ain * 100)` — that throws away 4 of the 6 decimals and
   * destroys the reproducibility guarantee the value exists for.
   */
  ain: number;

  /**
   * The engine's own measurement: the balance of the output stream, where
   * 0.500 is equilibrium. Present whenever the engine sends it.
   *
   * `ain` is derived from this through an absolute value and so cannot say
   * which side of equilibrium a reading sits on — 0.4687 and 0.5313 both give
   * AIN 0.9373. Read `pOutput` when the direction of the imbalance matters,
   * and compare it against 0.5 rather than against 1.
   */
  pOutput?: number;

  /** Distance from equilibrium as the engine reports it, when present. */
  deviation?: number;

  /** Stability regime (`status` on the wire). Not the AIN band. */
  status: StabilityStatus;

  /** AIN band (`ain_status` on the wire), when present on the API. */
  ainStatus?: AINStatus;

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
 * One operator family's verdict on a supplied matrix.
 */
export interface FamilyVerdict {
  /** Index into the engine's fixed family list. */
  family: number;
  /** The family's output bit for this matrix: 0 or 1. */
  bit: 0 | 1;
  /**
   * The fold reached an exact tie and the centre decided it. A tie means no
   * majority was found at all — a weaker result than a confident bit, and
   * anything presenting a verdict should say so rather than hide it.
   */
  tieBroken: boolean;
}

/**
 * Result of analysing one specific matrix.
 *
 * Deliberately carries no `ain` and no `pOutput`. Both describe how output
 * bits distribute across many sampled matrices; over a single matrix the
 * proportion is 0 or 1 and says nothing about balance. A score here would be
 * an invented number wearing the clothes of a measurement.
 */
export interface AnalyzeResult {
  /** Dimension of the matrix that was analysed. */
  n: number;
  /** Every family's verdict, in engine order. */
  families: FamilyVerdict[];
  /** How many families returned 1. */
  ones: number;
  /**
   * All four families agreed. Unanimity is a stronger result than a
   * three-to-one split, and the engine's pooled reading could not express
   * the difference between them.
   */
  unanimous: boolean;
  /**
   * Cells set to 1 in the matrix you sent, and the total.
   *
   * AUDIT 2026-07-31: the engine was swept over 3..=100. At every even
   * dimension the four family bits for an all-zeros matrix are identical to
   * those for an all-ones matrix - 49 of 49 even dimensions, none of the 49
   * odd ones - so the two most opposite inputs you can send came back with the
   * same verdict. Every paid ceiling except Pro's 25 is even: 16, 32, 48, 64,
   * 100.
   *
   * These three fields are your own matrix counted back to you, so a
   * degenerate input is visible as degenerate whatever the verdict says.
   *
   * Optional because an engine older than that sweep does not send them.
   * Check for undefined rather than defaulting to 0 - an inputOnes of 0 means
   * an all-zeros matrix, which is a real answer, not a missing one.
   */
  inputOnes?: number;
  cells?: number;
  /** Every cell identical. The verdict alone cannot show this at even n. */
  degenerate?: boolean;
  tokensUsed: number;
  computeMs?: number;
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
 * User account usage statistics.
 *
 * AUDIT 2026-05-14 (v2.0.3): rewritten to match the actual shape of
 * `zeropointlogic.io/api/user/me` (the only place quota lives — engine
 * never had a /usage endpoint). v2.0.0–2.0.2 callers reading
 * `usedToday` / `dailyLimit` / `resetAtToday` were receiving `undefined`
 * at runtime anyway (404 from the engine), so removing those fields here
 * is a no-op in practice. CLI made the same switch in v1.1.7.
 */
export interface Usage {
  /** Current plan tier ('free' | 'basic' | 'pro' | …) */
  plan: string;

  /** Tokens used this month */
  tokensUsed: number;

  /** Tokens remaining in the current monthly cycle */
  tokensRemaining: number;

  /** Monthly token quota for the current plan */
  tokensQuota: number;

  /** Bonus tokens balance (e.g. launch promos). 0 if none. */
  bonusBalance: number;

  /** Percentage of monthly quota consumed (0-100, server-computed) */
  percentUsed: number;

  /** Max matrix dimension allowed by the current plan (optional) */
  maxDimension?: number;

  /** When this snapshot was fetched */
  retrievedAt: Date;
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

  /**
   * Base URL for account / billing metadata calls (default:
   * https://zeropointlogic.io). Used by `getUsage()` because the engine
   * itself doesn't host /api/user/me — that endpoint lives on ZPL Main.
   * Override only for self-hosted ZPL deployments.
   */
  accountBaseUrl?: string;

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
 * Compute request payload — the exact JSON body `POST /compute` accepts.
 *
 * There is NO `matrix` parameter on the wire. `d` IS the matrix dimension;
 * the SDK's `compute({ matrix, samples })` helper derives `d` and `bias`
 * from the caller's matrix and posts this shape.
 */
export interface ComputeRequest {
  /** Matrix dimension, integer 3 – 100. Aliases accepted: N, n, dimension. */
  d: number;

  /** Input bias, float 0.0 – 1.0 */
  bias: number;

  /** Number of samples for analysis (optional) */
  samples?: number;

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
