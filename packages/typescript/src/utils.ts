/**
 * Utility functions for matrix operations and AIN interpretation
 * @module utils
 */

import type { BinaryMatrix, BiasLevel, AINStatus, ComputeResult } from './types.js';
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
    throw new ZPLValidationError(
      `Matrix must be at most 100x100 (got ${size}x${size}). The engine rejects dimension > 100; upgrade plan if you need higher d.`
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
 * Convert AIN score to bias level
 * @param ain - AI Neutrality Index (0-1)
 * @returns Bias level classification
 */
export function ainToBiasLevel(ain: number): BiasLevel {
  if (ain >= 0.8) return 'none';
  if (ain >= 0.7) return 'low';
  if (ain >= 0.5) return 'moderate';
  if (ain >= 0.3) return 'high';
  return 'critical';
}

/**
 * Convert AIN status to human-readable description
 * @param status - API status value
 * @returns Detailed interpretation string
 */
export function interpretStatus(status: AINStatus): string {
  const interpretations: Record<AINStatus, string> = {
    CERTIFIED_NEUTRAL:
      'Data demonstrates certified neutral properties. Highly reliable for unbiased analysis.',
    STABLE:
      'Stable neutrality detected. Suitable for most analytical purposes.',
    MODERATE_BIAS:
      'Moderate bias detected. Use with caution in decision-making. Recommend further analysis.',
    HIGH_BIAS:
      'High bias detected. Not recommended for critical decisions without mitigation strategies.',
    CRITICAL_BIAS:
      'Critical bias detected. Data is unsuitable for unbiased analysis. Immediate review required.',
  };

  return interpretations[status];
}

/**
 * Create a detailed interpretation of AIN result
 * @param ain - AI Neutrality Index (0-1)
 * @returns Human-friendly interpretation
 */
export function interpretAIN(ain: number): string {
  if (ain >= 0.95) {
    return 'Exceptional neutrality. System operates in near-perfect neutral equilibrium.';
  }
  if (ain >= 0.8) {
    return 'Excellent neutrality. System maintains strong neutral properties with minimal bias.';
  }
  if (ain >= 0.7) {
    return 'Good neutrality. System exhibits stable neutral behavior suitable for analysis.';
  }
  if (ain >= 0.6) {
    return 'Moderate neutrality. Some bias patterns detected but system remains generally neutral.';
  }
  if (ain >= 0.4) {
    return 'Weak neutrality. Significant bias present. Use with caution for critical decisions.';
  }
  if (ain >= 0.2) {
    return 'Poor neutrality. Strong bias detected. Recommend investigation and mitigation.';
  }
  return 'Critical bias. System heavily skewed. Immediate intervention required.';
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

const AIN_STATUSES: readonly AINStatus[] = [
  'CERTIFIED_NEUTRAL',
  'STABLE',
  'MODERATE_BIAS',
  'HIGH_BIAS',
  'CRITICAL_BIAS',
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

function coerceStatus(s: string | undefined): AINStatus {
  if (s && (AIN_STATUSES as readonly string[]).includes(s)) return s as AINStatus;
  return 'STABLE';
}

/**
 * Map raw JSON from POST /compute (snake_case engine fields) into {@link ComputeResult}
 * without derived fields `isNeutral` / `biasLevel` (client adds those).
 *
 * AUDIT 2026-05-13 (B2 + D4): `p_output` and `deviation` are read from
 * the wire response but NOT placed into the public ComputeResult — they
 * are trade-secret intermediates per the "Live Engine Only" / IP rules
 * (the MCP hides them; the SDK now matches). `tokens_remaining` is only
 * included when the engine actually returns it; absent means "n/a" and
 * the field stays `undefined` so consumers don't render misleading
 * "tokens=0 left" scare messages on a healthy account.
 */
export function normalizeEngineComputeResult(raw: Record<string, unknown>): Omit<ComputeResult, 'isNeutral' | 'biasLevel'> {
  const ain = pickNumber(raw, ['ain'], 0);
  const status = coerceStatus(pickString(raw, ['status']));
  const ainStatus = pickString(raw, ['ain_status', 'ainStatus']);
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
  return out;
}

/** Redact ZPL-style API key material from a string (logs / echoed errors). */
export function redactSecretsInText(text: string): string {
  return text.replace(/\bzpl_[su]_[a-z0-9_]{20,}/gi, 'zpl_[REDACTED]');
}
