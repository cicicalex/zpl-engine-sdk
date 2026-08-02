/**
 * ZPL Engine API Client
 * @module client
 */

import type {
  ZPLClientConfig,
  ComputeResult,
  AnalyzeResult,
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
  ainToBiasLevel,
  ainStatusToBiasLevel,
  isNeutralReading,
  redactSecretsInText,
} from './utils.js';

import { SDK_VERSION, ZPL_SDK_CLIENT_TYPE } from './meta.js';

// AUDIT 2026-05-14 (HIGH): the SDK Bearer-authorises every request to
// `baseUrl` + `accountBaseUrl` + the heartbeat URL. Any of those reading
// an attacker-controlled hostname (env var, malicious wrapper package
// config, committed .env) silently exfiltrates the user's API key on the
// first call. We allowlist by hostname suffix. Self-hosted / dev users
// can opt out with ZPL_SDK_ALLOW_PRIVATE=1 (acknowledging they're
// pointing at infrastructure they trust).
const ALLOWED_HOST_SUFFIXES = [
  'zeropointlogic.io',
];
function isAllowedHost(urlStr: string): boolean {
  try {
    const u = new URL(urlStr);
    if (typeof process !== 'undefined' && process.env?.ZPL_SDK_ALLOW_PRIVATE === '1') {
      return true;
    }
    if (u.protocol !== 'https:' && u.protocol !== 'http:') return false;
    // Strict suffix match: must end with one of the allowed bases AND
    // either match exactly or have a dot before the suffix (so
    // `evil-zeropointlogic.io` doesn't sneak in).
    return ALLOWED_HOST_SUFFIXES.some((base) => {
      return u.hostname === base || u.hostname.endsWith('.' + base);
    });
  } catch {
    return false;
  }
}
function sanitizeBaseUrl(candidate: string | undefined, fallback: string): string {
  if (!candidate) return fallback.replace(/\/$/, '');
  const cleaned = candidate.replace(/\/$/, '');
  if (isAllowedHost(cleaned)) return cleaned;
  // Don't silently use a rejected URL — fall back to the safe default.
  // Emitting to stderr so non-interactive consumers still see the warning.
  if (typeof process !== 'undefined' && process.stderr?.write) {
    process.stderr.write(
      `[zpl-sdk] Rejecting non-allowlisted URL "${candidate}" — falling back to "${fallback}". Set ZPL_SDK_ALLOW_PRIVATE=1 if self-hosted.\n`,
    );
  }
  return fallback.replace(/\/$/, '');
}

/**
 * ZPL Engine API Client
 * Provides methods to interact with the ZPL stability/neutrality analysis engine
 *
 * @example
 * ```typescript
 * const client = new ZPLClient({ apiKey: 'zpl_xxx' });
 *
 * const result = await client.compute({
 *   matrix: [[0,1,0],[1,0,1],[0,1,0]],
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
  // AUDIT 2026-05-14 (v2.0.3): see constructor — account-level metadata
  // (plan, quota, usage) lives on ZPL Main, not the engine.
  private accountBaseUrl: string;
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
    // AUDIT 2026-05-14 (HIGH): both `baseUrl` and `accountBaseUrl` accept
    // any string from caller config / env. The SDK sends `Authorization:
    // Bearer <apiKey>` to both on every call, so an attacker-supplied
    // hostname (committed .env, CI variable injection, malicious wrapper
    // package) silently exfiltrates the user's API key on the first
    // heartbeat. CLI + MCP enforce a host allowlist; SDK now matches.
    // Set ZPL_SDK_ALLOW_PRIVATE=1 only for genuine self-hosted setups.
    this.baseUrl = sanitizeBaseUrl(
      config.baseUrl,
      'https://engine.zeropointlogic.io',
    );
    // AUDIT 2026-05-14 (v2.0.3): account-level metadata (plan / quota /
    // usage) doesn't live on the engine — it lives on ZPL Main behind
    // /api/user/me. Pre-fix `getUsage()` hit `engine.zeropointlogic.io/usage`
    // which never existed (returned 404 "Not found"). CLI v1.1.7 made the
    // same move; SDK is now consistent.
    this.accountBaseUrl = sanitizeBaseUrl(
      config.accountBaseUrl,
      'https://zeropointlogic.io',
    );
    // AUDIT 2026-08-01: the default was 30000 - exactly the engine's compute
    // ceiling, and half its sweep ceiling. A deadline equal to the server's
    // is a coin flip over which side fires first, and losing means the
    // caller is billed for a computation they abandoned: the engine deducts
    // before it computes and refunds only on its own timeout. Waiting past
    // the engine turns the race into a 504 the engine issues and refunds.
    this.timeout = config.timeout || 65_000;
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
    // AUDIT 2026-05-14 (HIGH): ZPL_HEARTBEAT_URL was env-overridable
    // without host validation. A committed-by-mistake .env or a poisoned
    // CI variable could redirect the Bearer-Authorized POST to an
    // attacker host on every new ZPLClient() — silent key exfil. Now
    // gated by the same allowlist as baseUrl. Set ZPL_SDK_ALLOW_PRIVATE=1
    // to bypass for self-hosted/local-dev.
    const envHeartbeat =
      typeof process !== 'undefined' && process.env?.ZPL_HEARTBEAT_URL
        ? process.env.ZPL_HEARTBEAT_URL
        : undefined;
    const url = envHeartbeat
      ? sanitizeBaseUrl(envHeartbeat, 'https://zeropointlogic.io/api/auth/cli/heartbeat')
      : 'https://zeropointlogic.io/api/auth/cli/heartbeat';
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

    // Validate samples.
    //
    // AUDIT 2026-08-01: this accepted 1 to 1,000,000. The engine accepts
    // neither end of that: it does `samples.unwrap_or(1000).clamp(100, 50_000)`
    // and returns the clamped number without comment. So `samples: 5` ran 100
    // and `samples: 200_000` ran 50,000, in both cases silently, while the
    // caller's own record said otherwise — and a sample count is the lever
    // that decides how much work was paid for. The MCP tool schema and the
    // site's /api/compute both enforce 100..50000 and refuse outside it; this
    // is the same rule, so the three clients agree and nobody is told a number
    // ran that did not.
    if (!Number.isInteger(samples) || samples < 100 || samples > 50000) {
      throw new ZPLValidationError(
        'Samples must be an integer between 100 and 50,000 — the engine clamps ' +
          'anything outside that range and reports the clamped value, so a request ' +
          'outside it would not run what you asked for.'
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
    // AUDIT 2026-08-01: both derived fields were computed from thresholds the
    // engine does not use (`ain >= 0.7` for isNeutral, 0.8/0.7/0.5/0.3 for
    // biasLevel), so one result object could report `ainStatus:
    // 'MODERATE_BIAS'`, `isNeutral: true` and `biasLevel: 'low'` at once. They
    // now come from `ain_status` when the engine sent it — it is the engine's
    // own verdict on this reading — and from the engine's boundaries when it
    // did not. Deriving both from the same source is what keeps them from
    // disagreeing at a band edge.
    const result: ComputeResult = {
      ...core,
      isNeutral: isNeutralReading(core.ain, core.ainStatus),
      biasLevel:
        core.ainStatus !== undefined
          ? ainStatusToBiasLevel(core.ainStatus)
          : ainToBiasLevel(core.ain),
    };

    return result;
  }

  /**
   * Analyse a specific matrix — the engine sees your data.
   *
   * `compute()` does not transmit the matrix. It reduces it to a dimension and
   * a density of ones, sends those two numbers, and the engine generates fresh
   * random matrices at that density and reports on those. Two entirely
   * different inputs of equal density therefore receive the same answer, and
   * nothing in that response indicates the caller's data was never examined.
   *
   * This method posts the matrix itself. The engine runs the fold over it and
   * reports what each operator family concluded, whether any needed the centre
   * to break a tie, and how far the four agree.
   *
   * There is no AIN here, on purpose: one matrix is one observation, so a
   * proportion over it is 0 or 1 and would say nothing about balance.
   *
   * @param options - The matrix to analyse, plus optional timeout / key override
   * @returns Every family's verdict, with agreement
   *
   * @example
   * ```typescript
   * const result = await client.analyze({
   *   matrix: [[0,1,0],[1,0,1],[0,1,0]],
   * });
   * console.log(result.families);   // one entry per family
   * console.log(result.unanimous);  // did all four agree?
   * ```
   */
  async analyze(options: {
    matrix: BinaryMatrix;
    timeout?: number;
    apiKey?: string;
  }): Promise<AnalyzeResult> {
    const { matrix, timeout, apiKey } = options;

    // Validated here so a malformed matrix costs nothing: an invalid request
    // would be refused by the engine anyway, and spending a round trip to
    // learn that helps no one.
    try {
      validateMatrix(matrix);
    } catch (error) {
      throw new ZPLValidationError(
        `Invalid matrix: ${error instanceof Error ? error.message : 'unknown error'}`
      );
    }

    const payload: Record<string, unknown> = { matrix };
    if (apiKey) {
      payload.api_key = apiKey;
    }

    const raw = await this._request<{
      n: number;
      families: Array<{ family: number; bit: number; tie_broken: boolean }>;
      ones: number;
      unanimous: boolean;
      input_ones?: number;
      cells?: number;
      degenerate?: boolean;
      tokens_used: number;
      compute_ms?: number;
    }>('/analyze', { method: 'POST', body: JSON.stringify(payload) }, { timeout });

    return {
      n: raw.n,
      families: (raw.families ?? []).map((f) => ({
        family: f.family,
        bit: (f.bit === 1 ? 1 : 0) as 0 | 1,
        tieBroken: Boolean(f.tie_broken),
      })),
      ones: raw.ones,
      unanimous: raw.unanimous,
      // Left undefined when the engine predates the fields, rather than
      // defaulted to 0 - an inputOnes of 0 is an all-zeros matrix, a real
      // answer, and the two must not be confused.
      inputOnes: raw.input_ones,
      cells: raw.cells,
      degenerate: raw.degenerate,
      tokensUsed: raw.tokens_used,
      computeMs: raw.compute_ms,
    };
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
   * Get current usage and quota information.
   *
   * AUDIT 2026-05-14 (v2.0.3): re-routed from `engine.zeropointlogic.io/usage`
   * (which never existed and returned 404) to `zeropointlogic.io/api/user/me`.
   * CLI made the same switch in v1.1.7. The response shape is normalised
   * back to the SDK's `Usage` interface so v2.0.x callers see no breaking
   * change.
   *
   * @param timeout - Optional timeout override
   * @returns Usage object with current plan and token usage
   * @throws {ZPLError} on API error
   */
  async getUsage(timeout?: number): Promise<Usage> {
    type UserMeResponse = {
      user: { id: string; email: string; name: string | null; role: string; plan: string; plan_name: string };
      tokens: {
        remaining: number;
        used_this_month: number;
        monthly_quota: number;
        bonus_balance: number;
        total_available_this_cycle: number;
        percent_used: number;
        source?: string;
        engine_unreachable?: boolean;
      };
      limits?: { max_d: number; max_keys: number };
    };

    // Direct fetch to ZPL Main (not via this._request which is engine-scoped).
    // Same retry policy + timeout would be nice but the endpoint is so
    // reliable + cheap that a single attempt is enough. Mirrors CLI behaviour.
    const url = `${this.accountBaseUrl}/api/user/me`;
    const controller = new AbortController();
    const effectiveTimeout = timeout ?? this.timeout;
    const timer = setTimeout(() => controller.abort(), effectiveTimeout);
    try {
      const res = await this.fetchFn(url, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${this.apiKey}`,
          'User-Agent': this.userAgent,
          'X-ZPL-Client': this.zplClientType,
          'X-ZPL-Client-Version': this.zplClientVersion,
        },
        signal: controller.signal,
      });
      if (!res.ok) {
        const body = await res.text().catch(() => '');
        throw new Error(`ZPL Main /api/user/me returned ${res.status}: ${body.slice(0, 200)}`);
      }
      const data = (await res.json()) as UserMeResponse;

      // Map ZPL Main /api/user/me → SDK Usage interface.
      //
      // AUDIT 2026-08-01: `tokens.source` was declared in the response type
      // above and then dropped on the floor here, so the SDK reported an
      // unmeasured zero exactly as it reported a measured one. The server
      // added the field precisely because it cannot always read the engine,
      // and the CLI already branches on it in `whoami` and `quota`.
      //
      // `usageMeasured` whitelists the single value that means "read from the
      // engine" rather than blacklisting today's two failure values. A source
      // added on the server later then reads as not-measured until someone
      // decides otherwise, which is the safe direction — the CLI was tightened
      // the same way and for the same reason.
      const source = data.tokens.source;
      const usage: Usage = {
        plan: data.user.plan,
        // Engine "usage" semantically = monthly_quota − remaining, but we
        // also expose the bonus balance separately so callers can show it.
        tokensUsed: data.tokens.used_this_month,
        tokensRemaining: data.tokens.remaining,
        tokensQuota: data.tokens.monthly_quota,
        bonusBalance: data.tokens.bonus_balance,
        percentUsed: data.tokens.percent_used,
        maxDimension: data.limits?.max_d,
        source,
        usageMeasured: source === 'engine_log',
        engineUnreachable: data.tokens.engine_unreachable === true,
        retrievedAt: new Date(),
      };
      return usage;
    } finally {
      clearTimeout(timer);
    }
  }

  /**
   * Get available plans and pricing.
   *
   * AUDIT 2026-08-01: this fetched into `{plans: any[]}` and returned the
   * array unchanged while claiming it was `Plan[]`. The `any` hid the fact
   * that the engine sends `{name, max_d, tokens_per_month, max_keys,
   * price_usd, unlimited}` and the declared type promised `id`, `price`,
   * `dailyLimit`, `monthlyLimit` and `features` — so every field but `name`
   * was undefined at runtime and the README's `plan.features.join(', ')`
   * threw. The engine's fields are now mapped explicitly, which also means a
   * future rename on the wire fails here rather than silently downstream.
   *
   * @param timeout - Optional timeout override
   * @returns PlansResponse with all available plans
   * @throws {ZPLError} on API error
   */
  async getPlans(timeout?: number): Promise<PlansResponse> {
    const response = await this._request<{
      plans?: Array<{
        name?: string;
        max_d?: number;
        tokens_per_month?: number;
        max_keys?: number;
        price_usd?: number;
        unlimited?: boolean;
      }>;
    }>('/plans', { method: 'GET' }, { timeout });

    const num = (v: unknown): number =>
      typeof v === 'number' && Number.isFinite(v) ? v : 0;

    return {
      plans: (response.plans ?? []).map((p) => ({
        name: typeof p.name === 'string' ? p.name : '',
        maxDimension: num(p.max_d),
        tokensPerMonth: num(p.tokens_per_month),
        maxKeys: num(p.max_keys),
        priceUsd: num(p.price_usd),
        unlimited: p.unlimited === true,
      })),
      fetchedAt: new Date(),
    };
  }

  /**
   * Check API health and status.
   *
   * AUDIT 2026-08-01: this cast the raw body to `HealthResponse`, a type that
   * described `status: 'healthy' | 'degraded' | 'unhealthy'`, `uptime` and
   * `timestamp`. The engine sends `{status: "ok", version, uptime_seconds}`,
   * so the comparison every caller writes first — `status === 'healthy'` —
   * was permanently false and `uptime` was permanently undefined. Mapped from
   * the real body instead.
   *
   * `uptimeSeconds` is left undefined when the engine does not send it rather
   * than defaulted to 0, because 0 is a meaningful reading: a process that
   * started this second.
   *
   * @param timeout - Optional timeout override
   * @returns HealthResponse with service status
   * @throws {ZPLError} on API error
   */
  async getHealth(timeout?: number): Promise<HealthResponse> {
    const raw = await this._request<{
      status?: string;
      version?: string;
      uptime_seconds?: number;
    }>('/health', { method: 'GET' }, { timeout });

    const health: HealthResponse = {
      status: typeof raw.status === 'string' ? raw.status : 'unknown',
      version: typeof raw.version === 'string' ? raw.version : '',
    };
    if (typeof raw.uptime_seconds === 'number' && Number.isFinite(raw.uptime_seconds)) {
      health.uptimeSeconds = raw.uptime_seconds;
    }
    return health;
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
        // AUDIT 2026-08-02: this returned the engine's body untouched, and it
        // ends up on the thrown error as `details`. Measured: an engine error
        // echoing a key produced a generic `message` and a `details` holding
        // the key, a Bearer token and a Stripe key verbatim. The package
        // already shipped redactSecretsInText for exactly this and never
        // called it.
        //
        // Redacting the serialised form rather than walking the object keeps it
        // whole whatever shape the engine sends, including nested fields.
        const raw = (await response.json()) as Record<string, unknown>;
        return JSON.parse(redactSecretsInText(JSON.stringify(raw))) as Record<string, unknown>;
      }

      return null;
    } catch {
      return null;
    }
  }

  // AUDIT 2026-08-01: a private `_ainToBiasLevel` lived here with its own copy
  // of the thresholds, duplicating the exported `ainToBiasLevel` in utils.ts.
  // When the bands were realigned to the engine on 2026-07-31 only the
  // interpretation helper was updated, and this copy — the one that actually
  // populated every ComputeResult — kept the old numbers. Removed rather than
  // corrected: two copies of a threshold is how they drift apart.
}

/**
 * Check if an error is retryable.
 *
 * AUDIT 2026-08-01: `ZPLTimeoutError` was in this list, so a request that hit
 * the deadline was re-sent up to three more times. The engine deducts tokens
 * before it starts computing, so by the time the client's deadline fires the
 * call has already been charged and may still be running — every retry buys
 * the same work again. One user call became four billed ones.
 *
 * That is the same reasoning the CLI and the MCP were fixed with on the same
 * day (`api-client.ts`, `engine-client.ts`): an abort is terminal. The raised
 * default deadline now sits past the engine's own 60s ceiling, so a genuine
 * overrun comes back as the engine's 504 — which refunds — instead of as a
 * client-side abort. A deadline reached after that is a fact about this call,
 * not a transient the next attempt could fix.
 *
 * Network errors stay retryable: those fail before the engine answers, and the
 * common case is a connection that never carried the request at all.
 */
function isRetryableError(error: unknown): boolean {
  if (error instanceof ZPLTimeoutError) {
    return false;
  }

  if (error instanceof ZPLNetworkError) {
    return true;
  }

  if (error instanceof ZPLRateLimitError) {
    return true;
  }

  return false;
}
