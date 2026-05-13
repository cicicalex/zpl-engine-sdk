/**
 * AUDIT 2026-05-13 (BUG B1): this was hardcoded at '2.0.0' while
 * package.json shipped 2.0.2. Every heartbeat + `X-ZPL-Client-Version`
 * header reported the wrong version, so admin funnel dashboards
 * undercounted upgraded installs and version-conditional engine logic
 * treated fresh installs as 2 patches behind. Synced to current
 * package.json. TODO post-publish: generate at build time from
 * package.json so this can never drift again.
 *
 * @module meta
 */
export const SDK_VERSION = '2.0.2';

/** ADR 0002 default for `X-ZPL-Client` from this package. */
export const ZPL_SDK_CLIENT_TYPE = 'sdk-typescript' as const;
