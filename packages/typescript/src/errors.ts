/**
 * Error handling for ZPL Engine API
 * @module errors
 */

/**
 * Base error class for all ZPL SDK errors
 */
export class ZPLError extends Error {
  constructor(
    message: string,
    public code: string = 'ZPL_ERROR',
    public statusCode?: number,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ZPLError';
    Object.setPrototypeOf(this, ZPLError.prototype);
  }

  toJSON() {
    return {
      name: this.name,
      code: this.code,
      message: this.message,
      statusCode: this.statusCode,
      details: this.details,
    };
  }
}

/**
 * Thrown when API key is invalid or missing (401)
 */
export class ZPLAuthError extends ZPLError {
  constructor(message = 'Invalid or missing API key', details?: Record<string, unknown>) {
    super(message, 'ZPL_AUTH_ERROR', 401, details);
    this.name = 'ZPLAuthError';
    Object.setPrototypeOf(this, ZPLAuthError.prototype);
  }
}

/**
 * Thrown when request rate limit is exceeded (429)
 */
export class ZPLRateLimitError extends ZPLError {
  constructor(
    message = 'Rate limit exceeded',
    public retryAfter?: number,
    details?: Record<string, unknown>
  ) {
    super(message, 'ZPL_RATE_LIMIT', 429, details);
    this.name = 'ZPLRateLimitError';
    Object.setPrototypeOf(this, ZPLRateLimitError.prototype);
  }

  /**
   * Get retry delay in milliseconds
   */
  getRetryDelayMs(): number {
    return (this.retryAfter || 60) * 1000;
  }
}

/**
 * Thrown when token quota is exceeded.
 *
 * The engine returns this as HTTP 403 (not 402) with the message
 * "Token limit exceeded: X/Y used this month" — `parseApiError`
 * detects that shape and routes it here so SDK consumers can `catch`
 * by error class instead of string-matching.
 *
 * The default message now includes upgrade guidance so even consumers
 * who just `console.error(err.message)` end up showing the user how
 * to unblock themselves. This is the SDK equivalent of the MCP v4.1.4
 * quota nudge (engine-mcp commit d0a11dc).
 */
export class ZPLQuotaExceededError extends ZPLError {
  constructor(
    message?: string,
    public tokensRequired?: number,
    public tokensRemaining?: number,
    details?: Record<string, unknown>
  ) {
    const usage =
      tokensRequired && tokensRemaining !== undefined
        ? ` (need ${tokensRequired}, have ${tokensRemaining})`
        : '';
    const composed =
      message ??
      [
        `Monthly ZPL Engine quota exceeded${usage}.`,
        '',
        'Upgrade at https://zeropointlogic.io/pricing',
        '  • Basic   $10/mo   10,000 tokens',
        '  • Pro     $29/mo   50,000 tokens',
        '  • GamePro $69/mo  150,000 tokens',
        '',
        'Or buy a one-off pack: https://zeropointlogic.io/dashboard/billing',
      ].join('\n');
    // Engine returns 403 (Forbidden) for this case. Older docs claimed
    // 402; we use the real status code so `err.statusCode === 403`
    // matches what fetch saw.
    super(composed, 'ZPL_QUOTA_EXCEEDED', 403, details);
    this.name = 'ZPLQuotaExceededError';
    Object.setPrototypeOf(this, ZPLQuotaExceededError.prototype);
  }

  /**
   * Get tokens needed to complete request
   */
  getTokensNeeded(): number | undefined {
    if (this.tokensRequired && this.tokensRemaining) {
      return this.tokensRequired - this.tokensRemaining;
    }
    return undefined;
  }
}

/**
 * Thrown when request validation fails (400)
 */
export class ZPLValidationError extends ZPLError {
  constructor(message: string, details?: Record<string, unknown>) {
    super(message, 'ZPL_VALIDATION_ERROR', 400, details);
    this.name = 'ZPLValidationError';
    Object.setPrototypeOf(this, ZPLValidationError.prototype);
  }
}

/**
 * Thrown when network request times out
 */
export class ZPLTimeoutError extends ZPLError {
  constructor(
    message = 'Request timeout',
    public timeoutMs?: number,
    details?: Record<string, unknown>
  ) {
    super(message, 'ZPL_TIMEOUT', undefined, details);
    this.name = 'ZPLTimeoutError';
    Object.setPrototypeOf(this, ZPLTimeoutError.prototype);
  }
}

/**
 * Thrown when network request fails
 */
export class ZPLNetworkError extends ZPLError {
  constructor(
    message: string,
    public originalError?: Error,
    details?: Record<string, unknown>
  ) {
    super(message, 'ZPL_NETWORK_ERROR', undefined, details);
    this.name = 'ZPLNetworkError';
    Object.setPrototypeOf(this, ZPLNetworkError.prototype);
  }
}

/**
 * Type guard for ZPLError
 */
export function isZPLError(error: unknown): error is ZPLError {
  return error instanceof ZPLError;
}

/**
 * Type guard for ZPLAuthError
 */
export function isZPLAuthError(error: unknown): error is ZPLAuthError {
  return error instanceof ZPLAuthError;
}

/**
 * Type guard for ZPLRateLimitError
 */
export function isZPLRateLimitError(error: unknown): error is ZPLRateLimitError {
  return error instanceof ZPLRateLimitError;
}

/**
 * Type guard for ZPLQuotaExceededError
 */
export function isZPLQuotaExceededError(error: unknown): error is ZPLQuotaExceededError {
  return error instanceof ZPLQuotaExceededError;
}

/**
 * Build a clear message when the engine (or Cloudflare in front) returns HTML
 * or a non-JSON body. Mirrors the MCP client behaviour for operator-friendly text.
 */
export async function parseEngineHttpError(res: Response): Promise<string> {
  const ct = res.headers.get('content-type') ?? '';
  const isHtml = ct.includes('text/html');
  const cfRay = res.headers.get('cf-ray');
  const cfMitigated = res.headers.get('cf-mitigated');

  if (
    isHtml ||
    cfMitigated ||
    (cfRay && res.status >= 400 && !ct.includes('application/json'))
  ) {
    let snippet = '';
    try {
      const body = await res.text();
      if (/Just a moment|Checking your browser|cf-browser-verification|cf_chl_/i.test(body)) {
        snippet = 'Cloudflare browser challenge intercepted the request';
      } else if (/Attention Required|cloudflare/i.test(body)) {
        snippet = 'Cloudflare blocked the request';
      } else {
        snippet = 'Cloudflare returned an HTML page instead of JSON';
      }
    } catch {
      /* keep generic */
    }
    const ray = cfRay ? ` (cf-ray: ${cfRay})` : '';
    return [
      `Engine ${res.status} via Cloudflare${ray}: ${snippet}.`,
      '',
      'Likely causes:',
      '  • User-Agent blocked as a bot — use a browser-like User-Agent string.',
      '  • Rate limits — wait and retry.',
      '  • Check https://engine.zeropointlogic.io/health',
      ray ? `  • Include cf-ray ${cfRay} in bug reports.` : '',
    ]
      .filter(Boolean)
      .join('\n');
  }

  try {
    const err = (await res.json()) as { error?: string; message?: string };
    const msg = err.error ?? err.message ?? res.statusText;
    return `Engine error ${res.status}: ${msg}`;
  } catch {
    return `Engine error ${res.status}: ${res.statusText}`;
  }
}

/**
 * Parse error response from API and throw appropriate error
 */
export function parseApiError(
  status: number,
  data: unknown,
  message?: string
): ZPLError {
  const errorData = typeof data === 'object' && data !== null ? data : {};

  switch (status) {
    case 401:
      return new ZPLAuthError(
        message || 'Invalid API key',
        typeof errorData === 'object' ? (errorData as Record<string, unknown>) : undefined
      );

    case 402: {
      // Reserved for a future "payment required" semantic. Today the
      // engine returns 403 (see default branch below).
      const quotaErr = errorData as Record<string, unknown>;
      return new ZPLQuotaExceededError(
        message,
        quotaErr.tokensRequired as number | undefined,
        quotaErr.tokensRemaining as number | undefined,
        quotaErr.details as Record<string, unknown> | undefined
      );
    }

    case 429: {
      const rateLimitErr = errorData as Record<string, unknown>;
      return new ZPLRateLimitError(
        message || 'Rate limit exceeded',
        rateLimitErr.retryAfter as number | undefined,
        rateLimitErr.details as Record<string, unknown> | undefined
      );
    }

    case 400:
      return new ZPLValidationError(
        message || 'Invalid request',
        typeof errorData === 'object' ? (errorData as Record<string, unknown>) : undefined
      );

    default: {
      const obj =
        typeof errorData === 'object' && errorData !== null
          ? (errorData as Record<string, unknown>)
          : {};
      const fromBody =
        typeof obj.error === 'string'
          ? obj.error
          : typeof obj.message === 'string'
            ? obj.message
            : undefined;

      // Engine returns HTTP 403 with body "Token limit exceeded: X/Y used
      // this month" when a user runs out of monthly quota. The status code
      // implies "Forbidden" (auth issue) but the cause is actually billing,
      // so route it to ZPLQuotaExceededError instead of generic ZPLError.
      // Pulls the X / Y numbers out so the error exposes them as
      // tokensRemaining / tokensRequired for caller introspection.
      // (audit complet 12.05 — SDK discoverability sibling to MCP v4.1.4.)
      if (status === 403 && fromBody && /token limit exceeded/i.test(fromBody)) {
        const m = fromBody.match(/(\d+)\s*\/\s*(\d+)/);
        const used = m ? Number(m[1]) : undefined;
        const limit = m ? Number(m[2]) : undefined;
        return new ZPLQuotaExceededError(
          undefined, // use the default upgrade-friendly composed message
          undefined,
          used !== undefined && limit !== undefined ? limit - used : undefined,
          typeof errorData === 'object' ? (errorData as Record<string, unknown>) : undefined
        );
      }

      return new ZPLError(
        message || fromBody || 'API request failed',
        'ZPL_API_ERROR',
        status,
        typeof errorData === 'object' ? (errorData as Record<string, unknown>) : undefined
      );
    }
  }
}
