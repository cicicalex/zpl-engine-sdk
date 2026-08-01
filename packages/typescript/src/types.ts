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
 * Bias level classification — a five-label view of the engine's six
 * {@link AINStatus} bands.
 *
 * The engine has six bands and this scale has five labels, so exactly one
 * merge is needed. It is made at the top, between the two strongest neutral
 * bands, where the distinction is how neutral a reading is rather than how
 * biased:
 *
 *   none      CERTIFIED_NEUTRAL (>= 0.96) + HIGHLY_NEUTRAL (>= 0.90)
 *   low       NEUTRAL           (>= 0.80)
 *   moderate  MODERATE_BIAS     (>= 0.60)
 *   high      SIGNIFICANT_BIAS  (>= 0.40)
 *   critical  HIGH_BIAS         (<  0.40)
 *
 * Every boundary above is an engine boundary; none was chosen here. The split
 * that matters — between the labels that mean "not biased" (`none`, `low`) and
 * those that mean "biased" (`moderate`, `high`, `critical`) — is the engine's
 * own NEUTRAL floor of 0.80, so this scale cannot contradict `ain_status`.
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

  /**
   * Computed client-side: does the engine consider this reading neutral?
   *
   * AUDIT 2026-08-01: this was `ain >= 0.7`, below the engine's NEUTRAL floor
   * of 0.80. At ain 0.75 one object said `ainStatus: 'MODERATE_BIAS'` and
   * `isNeutral: true` at the same time — the SDK contradicting the engine
   * inside a single result. Now taken from `ainStatus` when the engine sent a
   * band, and from the engine's own 0.80 floor when it did not.
   */
  isNeutral: boolean;

  /**
   * Computed client-side: the AIN band expressed on the five-point bias scale.
   *
   * Derived from `ainStatus` when present, otherwise from `ain` using the
   * engine's boundaries. The neutral/biased split sits at 0.80 in both fields,
   * so `biasLevel` and `ainStatus` can no longer disagree — see
   * {@link ainToBiasLevel} for how six engine bands map onto five labels.
   */
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

  /**
   * How the server obtained `tokensUsed` — `tokens.source` on the wire.
   *
   * AUDIT 2026-08-01: ZPL Main added this field because three different
   * server-side failures all produce `used_this_month: 0`, and that is also
   * what a genuinely idle account produces. Measured on production: 200 tokens
   * were spent on the engine and this endpoint reported 0 used, before and
   * after. Only `"engine_log"` means the number was actually read from the
   * engine's usage log. `"engine_user_not_found"` means the two databases
   * disagree about who this account is; `"user_table_fallback"` means the
   * engine could not be reached and the figure came from a copy the drift cron
   * reconciles hourly.
   *
   * The SDK parsed this field's sibling fields and dropped this one, so an
   * unmeasured zero arrived indistinguishable from a measured one. Enforcement
   * does not go through this path — the engine deducts atomically on every
   * request — so a wrong zero here is the only warning a caller gets before
   * being refused.
   *
   * Prefer {@link Usage.usageMeasured} over comparing this string yourself: a
   * value added on the server later must read as *not measured* until someone
   * decides otherwise, which is how the CLI's `whoami` and `quota` treat it.
   */
  source?: string;

  /**
   * True only when `source === 'engine_log'` — i.e. `tokensUsed`,
   * `tokensRemaining` and `percentUsed` are readings rather than guesses.
   *
   * When false, show them as unknown rather than as numbers. They are still
   * populated because zero is the only figure the server has, not because it
   * is the right one.
   */
  usageMeasured: boolean;

  /**
   * The server could not reach the engine database while answering
   * (`tokens.engine_unreachable`). The numbers may be stale by up to an hour.
   */
  engineUnreachable: boolean;

  /** When this snapshot was fetched */
  retrievedAt: Date;
}

/**
 * One plan, exactly as `GET /plans` returns it.
 *
 * AUDIT 2026-08-01: every field of this interface except `name` described an
 * API that has never existed. It declared `id`, `price`, `dailyLimit`,
 * `monthlyLimit` and `features` as required, while the engine's plans handler
 * serialises `{name, max_d, tokens_per_month, max_keys, price_usd, unlimited}`
 * and nothing else. `getPlans()` handed the parsed body straight back without
 * mapping, so at runtime only `name` was ever present: `plan.price` was
 * `undefined`, and the `plan.features.join(...)` in the README threw a
 * TypeError on the first line anyone copied out of it.
 *
 * The fields below are the engine's, renamed to this SDK's camelCase and
 * mapped in `getPlans()`. Nothing is invented to fill the gaps: the plans
 * response carries no daily limit (the engine keeps `tokens_per_day`
 * internally and does not serialise it) and no feature list at all, so neither
 * appears here.
 */
export interface Plan {
  /** Plan name as the engine spells it: Free, Basic, Pro … Enterprise XL. */
  name: string;

  /** Largest matrix dimension this plan may send (`max_d` on the wire). */
  maxDimension: number;

  /** Monthly token allowance (`tokens_per_month`). */
  tokensPerMonth: number;

  /** Simultaneously active API keys this plan may hold (`max_keys`). */
  maxKeys: number;

  /**
   * Monthly price in USD (`price_usd`). USD is the only currency in the
   * system — Stripe charges USD and no EUR price exists in the engine plan
   * table, the site constants, or this response.
   */
  priceUsd: number;

  /**
   * The engine's `unlimited` flag — not an absence of a cap. The engine sets
   * it for any plan whose `tokens_per_month` is at or above 50,000,000, which
   * today is Enterprise XL alone, and 50,000,000 is exactly the ceiling that
   * plan is metered against. `tokensPerMonth` is the number that is enforced.
   */
  unlimited: boolean;
}

/**
 * Plans catalog
 */
export interface PlansResponse {
  plans: Plan[];
  fetchedAt: Date;
}

/**
 * Health check response from `GET /health`.
 *
 * AUDIT 2026-08-01: this declared `status: 'healthy' | 'degraded' |
 * 'unhealthy'`, `uptime: number` and `timestamp: string`. The engine's health
 * handler returns `{status: "ok", version, uptime_seconds}` — so
 * `health.status === 'healthy'` could never be true, `health.uptime` was
 * always `undefined`, and any arithmetic on it produced NaN. Corrected to
 * what the endpoint sends.
 */
export interface HealthResponse {
  /**
   * The engine sends the literal string `"ok"` and has no other value: the
   * handler builds the response from a constant, so there is no degraded or
   * unhealthy reading to branch on. A successful `getHealth()` call — rather
   * than the contents of this field — is what tells you the engine answered.
   */
  status: string;

  /** Engine version (its own `CARGO_PKG_VERSION`). */
  version: string;

  /**
   * Seconds since the engine process started (`uptime_seconds` on the wire).
   *
   * Optional because an engine older than this field does not send it, and
   * absent is not zero — zero would mean the process restarted this second.
   * There is no uptime *percentage* on this endpoint and no timestamp; the
   * engine measures neither.
   */
  uptimeSeconds?: number;
}

/**
 * Request options for compute operations
 */
export interface ComputeOptions {
  /**
   * Number of samples for statistical analysis (default: 1000).
   *
   * The engine accepts 100 – 50,000 and silently clamps anything outside that
   * range, returning the clamped figure. The SDK rejects out-of-range values
   * rather than letting a caller believe 5 samples or 200,000 samples ran.
   */
  samples?: number;

  /**
   * Request timeout in milliseconds (default: 65000 — the engine's 60s sweep
   * ceiling plus network headroom; see ZPLClientConfig.timeout).
   */
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

  /**
   * Default timeout in milliseconds (default: 65000).
   *
   * Must stay ABOVE the engine's own ceilings — 30s for /compute, 60s for
   * /sweep — plus headroom for the network. The engine deducts tokens before
   * it computes and refunds only on a timeout it issues itself, so a client
   * that gives up first abandons a call the caller has already paid for. A
   * client that waits gets the engine's 504, which does refund.
   */
  timeout?: number;

  /**
   * Number of retries for failed requests (default: 3).
   *
   * Retries cover transport failures and 5xx/429 responses. A request that
   * hits the deadline is never retried: see the terminal-abort note in
   * client.ts.
   */
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
