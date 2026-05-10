/**
 * ZPL Engine TypeScript SDK
 * Official SDK for the Zero Point Logic Engine API
 *
 * @packageDocumentation
 * @example
 * ```typescript
 * import { ZPLClient, pricesToMatrix } from '@zeropointlogic/sdk';
 *
 * const client = new ZPLClient({ apiKey: 'zpl_xxx' });
 *
 * // Analyze price data for bias
 * const prices = [100, 102, 101, 103, 105];
 * const matrix = pricesToMatrix(prices);
 * const result = await client.compute({ matrix, samples: 1000 });
 *
 * console.log(`AIN: ${result.ain}`);      // 0.73
 * console.log(`Status: ${result.status}`); // STABLE
 * ```
 */

// Main client
export { ZPLClient } from './client.js';

// Types
export type {
  AINStatus,
  BiasLevel,
  BinaryMatrix,
  ComputeResult,
  BatchComputeResult,
  ComputeOptions,
  BatchComputeOptions,
  Usage,
  Plan,
  PlansResponse,
  HealthResponse,
  ZPLClientConfig,
  RetryPolicy,
  RequestMetadata,
  ComputeRequest,
  ErrorResponse,
} from './types.js';

// Errors
export {
  ZPLError,
  ZPLAuthError,
  ZPLRateLimitError,
  ZPLQuotaExceededError,
  ZPLValidationError,
  ZPLTimeoutError,
  ZPLNetworkError,
  isZPLError,
  isZPLAuthError,
  isZPLRateLimitError,
  isZPLQuotaExceededError,
  parseApiError,
  parseEngineHttpError,
} from './errors.js';

export { SDK_VERSION, ZPL_SDK_CLIENT_TYPE } from './meta.js';

// Utilities
export {
  pricesToMatrix,
  matrixFromReturns,
  createRandomMatrix,
  validateMatrix,
  ainToBiasLevel,
  interpretStatus,
  interpretAIN,
  generateRequestId,
  calculateBackoffDelay,
  isRetryableStatus,
  formatMatrix,
  sleep,
  normalizeEngineComputeResult,
  redactSecretsInText,
} from './utils.js';
