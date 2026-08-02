/**
 * Utility functions for matrix operations and AIN interpretation
 * @module utils
 */

import type {
  BinaryMatrix,
  BiasLevel,
  AINStatus,
  StabilityStatus,
  ComputeResult,
} from './types.js';
import { ZPLValidationError } from './errors.js';

/**
 * Convert an array of prices to a binary matrix using a sliding window
 * over return direction (1 = price up, 0 = down or unchanged).
 *
 * Output shape is `(prices.length - window) × window`. For a *square*
 * matrix (which `ZPLClient.compute` requires) supply exactly
 * `2 * window` prices — e.g. window=20 → 40 prices → 20x20.
 *
 * @param prices - Numerical price series, ordered oldest → newest
 * @param window - Sliding-window size (default: 20)
 * @returns Binary matrix; empty rows are not possible because we throw first
 * @throws {ZPLValidationError} if prices.length is not strictly greater than window
 */
export function pricesToMatrix(prices: number[], window = 20): BinaryMatrix {
  if (!Array.isArray(prices) || prices.length < 2) {
    throw new ZPLValidationError('Prices array must have at least 2 elements');
  }

  // Pre-fix: this used `prices.length < window`, which let
  // `prices.length === window` slip through and produce an empty matrix.
  // Callers then hit `matrix[0].length` on `[]` → TypeError. Now we require
  // strictly more, so the loop below produces at least one row.
  if (prices.length <= window) {
    throw new ZPLValidationError(
      `Prices array length (${prices.length}) must be greater than window size (${window}). ` +
        `For a square ${window}x${window} matrix supply ${2 * window} prices.`
    );
  }

  const matrix: BinaryMatrix = [];

  for (let i = window; i < prices.length; i++) {
    const row: number[] = [];

    for (let j = i - window; j < i; j++) {
      // 1 if price moved up, 0 if down or same
      row.push(prices[j + 1] > prices[j] ? 1 : 0);
    }

    matrix.push(row);
  }

  return matrix;
}

/**
 * Convert daily returns array to a binary matrix
 * @param returns - Array of daily returns (e.g., [0.02, -0.01, 0.03])
 * @returns Binary matrix (0 = negative/zero return, 1 = positive return)
 * @throws {ZPLValidationError} if returns array is invalid
 */
export function matrixFromReturns(returns: number[]): BinaryMatrix {
  if (!Array.isArray(returns) || returns.length === 0) {
    throw new ZPLValidationError('Returns array must be non-empty');
  }

  const matrix: BinaryMatrix = [];

  for (let i = 0; i < returns.length; i += Math.ceil(Math.sqrt(returns.length))) {
    const row: number[] = [];
    const windowSize = Math.ceil(Math.sqrt(returns.length));

    for (let j = 0; j < windowSize && i + j < returns.length; j++) {
      row.push(returns[i + j] > 0 ? 1 : 0);
    }

    if (row.length > 0) {
      // Pad row to square matrix
      while (row.length < windowSize) {
        row.push(0);
      }
      matrix.push(row);
    }
  }

  return matrix;
}

/**
 * Create a random binary matrix for testing
 * @param n - Size of matrix (n x n)
 * @param seed - Optional seed for deterministic generation
 * @returns Random binary matrix
 */
export function createRandomMatrix(n: number, seed?: number): BinaryMatrix {
  if (!Number.isInteger(n) || n < 1 || n > 1000) {
    throw new ZPLValidationError('Matrix size must be an integer between 1 and 1000');
  }

  const matrix: BinaryMatrix = [];
  let pseudoRandom = seed || Math.random();

  for (let i = 0; i < n; i++) {
    const row: number[] = [];
    for (let j = 0; j < n; j++) {
      // Linear congruential generator for deterministic randomness if seed provided
      if (seed !== undefined) {
        pseudoRandom = (pseudoRandom * 1103515245 + 12345) % 2147483648;
        row.push((pseudoRandom % 2) as 0 | 1);
      } else {
        row.push(Math.random() > 0.5 ? 1 : 0);
      }
    }
    matrix.push(row);
  }

  return matrix;
}

/**
 * Validate a binary matrix
 *
 * Engine constraints (verified against engine 3.1.0):
 *   - shape must be square N x N
 *   - 3 <= N <= 100  (engine returns HTTP 400 "D must be between 3 and 100"
 *     when violated; we fail fast client-side so the user sees a clear
 *     ZPLValidationError instead of a confusing API error)
 *   - every cell must be 0 or 1 (binary)
 *
 * @param matrix - Matrix to validate
 * @throws {ZPLValidationError} if matrix is invalid
 */
export function validateMatrix(matrix: BinaryMatrix): void {
  if (!Array.isArray(matrix) || matrix.length === 0) {
    throw new ZPLValidationError('Matrix must be a non-empty 2D array');
  }

  const size = matrix.length;

  if (size < 3) {
    throw new ZPLValidationError(
      `Matrix must be at least 3x3 (got ${size}x${size}). The engine requires dimension >= 3.`
    );
  }
  if (size > 100) {
    // AUDIT 2026-07-31: this said "upgrade plan if you need higher d", which is
    // advice no amount of money can follow. 100 is a hard engine constant —
    // BinaryMatrix::MAX_N — and the request is refused before any plan is
    // consulted. The most expensive plan, Enterprise XL at $999/mo, grants
    // exactly max_d 100, so there is nothing above this to buy.
    //
    // The message also conflated two different limits. Below 100, the per-plan
    // ceiling (9/16/25/32/48/64/100) is real and upgrading does raise it — and
    // the engine says so itself, with "Dimension X exceeds plan limit of Y".
    // That is the case where the old sentence would have been useful, and it is
    // the one case it never appeared in.
    throw new ZPLValidationError(
      `Matrix must be at most 100x100 (got ${size}x${size}). 100 is the engine's ` +
        `hard maximum, not a plan limit — no plan accepts a larger matrix, ` +
        `including the highest. Reduce the matrix instead.`
    );
  }

  for (let i = 0; i < matrix.length; i++) {
    if (!Array.isArray(matrix[i])) {
      throw new ZPLValidationError(`Row ${i} is not an array`);
    }

    if (matrix[i].length !== size) {
      throw new ZPLValidationError(
        `Matrix must be square: ${size} rows but row ${i} has ${matrix[i].length} columns`
      );
    }

    for (let j = 0; j < matrix[i].length; j++) {
      const val = matrix[i][j];
      if (typeof val !== 'number' || (val !== 0 && val !== 1)) {
        throw new ZPLValidationError(
          `Matrix[${i}][${j}] = ${val}, must be 0 or 1`
        );
      }
    }
  }
}

/**
 * Convert an AIN score to a bias level, on the engine's boundaries.
 *
 * AUDIT 2026-08-01: this used 0.8 / 0.7 / 0.5 / 0.3, none of which is a band
 * edge the engine recognises, and the 2026-07-31 pass that aligned
 * {@link interpretAIN} to `ain_status` left this function and its private
 * duplicate inside the client untouched. The result was a single object
 * disagreeing with itself: at ain 0.75 the engine says `MODERATE_BIAS` and
 * this said `'low'`, which is the label for a reading with almost no bias.
 * A caller switching on `biasLevel` was told the opposite of what the engine
 * reported for the same number.
 *
 * The boundaries below are the engine's own (`zpl-core/src/ain.rs`), collapsed
 * onto five labels exactly once — see {@link BiasLevel} for why the merge is
 * made where it is. Nothing between the labels is a threshold chosen here.
 *
 * @param ain - AI Neutrality Index (0-1)
 * @returns Bias level classification
 */
export function ainToBiasLevel(ain: number): BiasLevel {
  if (ain >= 0.9) return 'none';
  if (ain >= 0.8) return 'low';
  if (ain >= 0.6) return 'moderate';
  if (ain >= 0.4) return 'high';
  return 'critical';
}

/**
 * Convert an `ain_status` band to a bias level.
 *
 * Preferred over {@link ainToBiasLevel} whenever the engine sent a band: the
 * band IS the engine's classification of that reading, so deriving from it
 * cannot round to the far side of a boundary the way re-deriving from the
 * float can.
 *
 * @param status - AIN band value (`ain_status`), not the stability `status`
 */
export function ainStatusToBiasLevel(status: AINStatus): BiasLevel {
  const map: Record<AINStatus, BiasLevel> = {
    CERTIFIED_NEUTRAL: 'none',
    HIGHLY_NEUTRAL: 'none',
    NEUTRAL: 'low',
    MODERATE_BIAS: 'moderate',
    SIGNIFICANT_BIAS: 'high',
    HIGH_BIAS: 'critical',
  };
  return map[status];
}

/**
 * Is this reading neutral by the engine's definition?
 *
 * AUDIT 2026-08-01: the client computed `ain >= 0.7`, which sits inside the
 * engine's MODERATE_BIAS band (0.60 – 0.80). Every reading between 0.70 and
 * 0.80 was reported as neutral by the SDK and as biased by the engine that
 * produced it, in the same result object.
 *
 * When the engine sent a band, that band decides: the three neutral bands are
 * the ones without `BIAS` in their name. Without a band, the engine's NEUTRAL
 * floor of 0.80 decides.
 *
 * @param ain - AI Neutrality Index (0-1)
 * @param ainStatus - the engine's band for this reading, when it sent one
 */
export function isNeutralReading(ain: number, ainStatus?: AINStatus): boolean {
  if (ainStatus !== undefined) return !ainStatus.includes('BIAS');
  return ain >= 0.8;
}

/**
 * Convert an `ain_status` band to a human-readable description
 * @param status - AIN band value (`ain_status`), not the stability `status`
 * @returns Detailed interpretation string
 */
export function interpretStatus(status: AINStatus): string {
  const interpretations: Record<AINStatus, string> = {
    CERTIFIED_NEUTRAL:
      'Data demonstrates certified neutral properties. Highly reliable for unbiased analysis.',
    HIGHLY_NEUTRAL:
      'Highly neutral. Suitable for most analytical purposes.',
    NEUTRAL:
      'Neutral. Bias is within the normal band for analytical use.',
    MODERATE_BIAS:
      'Moderate bias detected. Use with caution in decision-making. Recommend further analysis.',
    SIGNIFICANT_BIAS:
      'Significant bias detected. Not recommended for critical decisions without mitigation strategies.',
    HIGH_BIAS:
      'High bias detected. Data is unsuitable for unbiased analysis. Immediate review required.',
  };

  return interpretations[status];
}

/**
 * Human-readable interpretation of an AIN reading.
 *
 * AUDIT 2026-07-31: this used bands 0.95 / 0.8 / 0.7 / 0.6 / 0.4 / 0.2 while
 * the Python SDK used 0.85 / 0.70 / 0.55 / 0.40 / 0.25, and neither matched the
 * engine's own ain_status. Measured, same readings, both SDKs:
 *
 *   ain 0.87  TS "Excellent neutrality"   Python "Perfectly Neutral"   engine NEUTRAL
 *   ain 0.75  TS "Good neutrality"        Python "Highly Neutral"      engine MODERATE_BIAS
 *   ain 0.58  TS "Weak neutrality"        Python "Moderately Neutral"  engine SIGNIFICANT_BIAS
 *
 * So the same number described differently depending on which language a team
 * happened to use, and both softer than the engine that produced it. A caller
 * comparing notes with a colleague on the other SDK would find they disagreed
 * about the same result.
 *
 * These are the engine's six bands and its boundaries. The wording is shared
 * with the Python SDK word for word.
 *
 * @param ain - AI Neutrality Index (0-1)
 */
export function interpretAIN(ain: number): string {
  if (ain >= 0.96) {
    return 'Certified neutral. The reading sits in the engine\'s highest band.';
  }
  if (ain >= 0.9) {
    return 'Highly neutral. Strongly balanced, close to equilibrium.';
  }
  if (ain >= 0.8) {
    return 'Neutral. Balanced within the engine\'s neutral band.';
  }
  if (ain >= 0.6) {
    return 'Moderate bias. A noticeable imbalance the engine reports as bias, not neutrality.';
  }
  if (ain >= 0.4) {
    return 'Significant bias. Substantial imbalance; treat conclusions with caution.';
  }
  return 'High bias. Severe imbalance.';
}

/**
 * Generate a unique request ID for tracking
 * @returns Request ID (UUID v4)
 */
export function generateRequestId(): string {
  // Simple UUID v4 implementation
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Calculate exponential backoff delay
 * @param retryCount - Current retry attempt (0-based)
 * @param baseDelayMs - Base delay in milliseconds
 * @param maxDelayMs - Maximum delay in milliseconds
 * @param multiplier - Backoff multiplier
 * @returns Delay in milliseconds
 */
export function calculateBackoffDelay(
  retryCount: number,
  baseDelayMs = 100,
  maxDelayMs = 10000,
  multiplier = 2
): number {
  const delay = baseDelayMs * Math.pow(multiplier, retryCount);
  // Add jitter (±10%)
  const jitter = delay * (0.9 + Math.random() * 0.2);
  return Math.min(jitter, maxDelayMs);
}

/**
 * Check if a status code is retryable
 * @param statusCode - HTTP status code
 * @returns true if request should be retried
 */
export function isRetryableStatus(statusCode: number): boolean {
  // Retry on 5xx errors and specific 4xx errors
  return (
    statusCode >= 500 ||
    statusCode === 408 || // Request Timeout
    statusCode === 429 // Too Many Requests
  );
}

/**
 * Format matrix for display/logging
 * @param matrix - Binary matrix
 * @param maxRows - Maximum rows to display
 * @returns Formatted string
 */
export function formatMatrix(matrix: BinaryMatrix, maxRows = 5): string {
  const displayRows = Math.min(maxRows, matrix.length);
  const rows: string[] = [];

  for (let i = 0; i < displayRows; i++) {
    rows.push('[ ' + matrix[i].join(' ') + ' ]');
  }

  if (matrix.length > displayRows) {
    rows.push(`... (${matrix.length - displayRows} more rows)`);
  }

  return `${matrix.length}x${matrix[0]?.length || 0} Matrix:\n${rows.join('\n')}`;
}

/**
 * Sleep utility for delays
 * @param ms - Milliseconds to sleep
 * @returns Promise that resolves after delay
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * `status` — stability regime. Plain `INHIBITED` is not a member.
 * Pre-fix this list mixed the two enums, so a real `INHIBITED_HIGH` /
 * `INHIBITED_LOW` / `ACTIVE` from the engine was silently rewritten to
 * `STABLE` — the SDK reported the opposite of what the engine said.
 */
const STABILITY_STATUSES: readonly StabilityStatus[] = [
  'STABLE',
  'ACTIVE',
  'INHIBITED_HIGH',
  'INHIBITED_LOW',
];

/** `ain_status` — AIN band. A different field from `status`. */
const AIN_STATUSES: readonly AINStatus[] = [
  'CERTIFIED_NEUTRAL',
  'HIGHLY_NEUTRAL',
  'NEUTRAL',
  'MODERATE_BIAS',
  'SIGNIFICANT_BIAS',
  'HIGH_BIAS',
];

function pickNumber(raw: Record<string, unknown>, keys: string[], fallback: number): number {
  for (const k of keys) {
    const v = raw[k];
    if (typeof v === 'number' && Number.isFinite(v)) return v;
  }
  return fallback;
}

function pickString(raw: Record<string, unknown>, keys: string[]): string | undefined {
  for (const k of keys) {
    const v = raw[k];
    if (typeof v === 'string' && v.length > 0) return v;
  }
  return undefined;
}

function coerceStatus(s: string | undefined): StabilityStatus {
  if (s && (STABILITY_STATUSES as readonly string[]).includes(s)) return s as StabilityStatus;
  return 'STABLE';
}

function coerceAinStatus(s: string | undefined): AINStatus | undefined {
  if (s && (AIN_STATUSES as readonly string[]).includes(s)) return s as AINStatus;
  return undefined;
}

/**
 * Map raw JSON from POST /compute (snake_case engine fields) into {@link ComputeResult}
 * without derived fields `isNeutral` / `biasLevel` (client adds those).
 *
 * AUDIT 2026-05-13 (B2 + D4): `p_output` and `deviation` were read from the
 * wire response but NOT placed into the public ComputeResult, treated as
 * trade-secret intermediates because the MCP hid them.
 *
 * AUDIT 2026-07-30: reversed, after checking what the wire actually carries.
 * The engine's own HTTP response serialises p_output and deviation to every
 * caller holding a key, so both have been public since the API shipped.
 * Withholding them here hid them from the one audience reading through the
 * SDK, while anyone calling the endpoint directly had them all along. The
 * owner's position, asked directly: the calculation stays secret, the numbers
 * it produces do not — a single output coefficient reveals no method.
 *
 * It matters beyond visibility. `p_output` is the engine's actual measurement,
 * output balance with 0.500 as equilibrium; `ain` is derived from it through
 * an absolute value and therefore cannot say which side of equilibrium a
 * reading sits on. p_output 0.4687 and 0.5313 both come back as AIN 0.9373.
 * For a method whose purpose is finding a stable centre, which way it leans is
 * half the answer, and the SDK was discarding that half.
 *
 * Both stay optional: absent means the engine did not send them, which is not
 * the same as a balance of zero. `tokens_remaining` is only
 * included when the engine actually returns it; absent means "n/a" and
 * the field stays `undefined` so consumers don't render misleading
 * "tokens=0 left" scare messages on a healthy account.
 */
export function normalizeEngineComputeResult(raw: Record<string, unknown>): Omit<ComputeResult, 'isNeutral' | 'biasLevel'> {
  const ain = pickNumber(raw, ['ain'], 0);
  const status = coerceStatus(pickString(raw, ['status']));
  const ainStatus = coerceAinStatus(pickString(raw, ['ain_status', 'ainStatus']));
  const computeMsRaw = pickNumber(raw, ['compute_ms', 'computeMs'], NaN);
  const tokensUsed = Math.round(pickNumber(raw, ['tokens_used', 'tokensUsed'], 0));
  // tokens_remaining: only set when engine actually included it. We
  // distinguish absent (undefined) from zero so the "you have N left"
  // hint only shows when it's real.
  const tokensRemainingPresent = 'tokens_remaining' in raw || 'tokensRemaining' in raw;
  const tokensRemainingValue = tokensRemainingPresent
    ? Math.round(pickNumber(raw, ['tokens_remaining', 'tokensRemaining'], 0))
    : undefined;

  const out: Omit<ComputeResult, 'isNeutral' | 'biasLevel'> = {
    ain,
    status,
    tokensUsed,
  };
  if (tokensRemainingValue !== undefined) out.tokensRemaining = tokensRemainingValue;
  if (ainStatus !== undefined) out.ainStatus = ainStatus;
  if (Number.isFinite(computeMsRaw)) out.computeMs = computeMsRaw;

  // Only when the engine actually sent them. A missing measurement must not
  // arrive as 0, which would claim the output stream was entirely zeros — a
  // real reading, and a badly wrong one.
  const pOutputRaw = pickNumber(raw, ['p_output', 'pOutput'], NaN);
  if (Number.isFinite(pOutputRaw)) out.pOutput = pOutputRaw;
  const deviationRaw = pickNumber(raw, ['deviation'], NaN);
  if (Number.isFinite(deviationRaw)) out.deviation = deviationRaw;
  return out;
}

/**
 * Redact secret-shaped material from a string (logs / echoed errors).
 *
 * AUDIT 2026-08-02: this covered ZPL keys and nothing else, and the SDK never
 * called it — it was exported for consumers and skipped internally. Measured
 * against an engine that echoed a key back in an error body, which the MCP's
 * own notes record as having happened for real: the thrown error carried
 * `message: "Invalid request"` and a `details` field holding the engine's text
 * verbatim, ZPL key, Bearer token and Stripe key intact. A consumer logging the
 * error object — the ordinary thing to do — writes all three down.
 *
 * The shapes now match the set the CLI and the MCP redact, checked by the same
 * corpus in all three suites. The quote exclusion on the Bearer pattern is
 * deliberate and copied along with it: its twins run over serialised JSON,
 * where a greedier token swallows the closing quote.
 */
export function redactSecretsInText(text: string): string {
  return text
    .replace(/zpl_[us]_(?:[a-z]+_)?[a-f0-9]{20,}/gi, 'zpl_[REDACTED]')
    .replace(/Bearer\s+[^\s"]+/gi, 'Bearer [REDACTED]')
    .replace(/sk-[A-Za-z0-9_-]+/gi, '[REDACTED]')
    .replace(/sk_(?:live|test)_[A-Za-z0-9_-]+/gi, '[REDACTED]')
    .replace(/gsk_[A-Za-z0-9_-]+/gi, '[REDACTED]');
}
