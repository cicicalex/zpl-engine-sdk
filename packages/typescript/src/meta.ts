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
/**
 * AUDIT 2026-07-31: it drifted again, exactly as the note above predicted. The
 * package was bumped to 2.1.0 for this release and this constant was not, so
 * every `X-ZPL-Client-Version` header would have reported 2.0.6 from a 2.1.0
 * install - permanently, since a published tarball cannot be edited.
 *
 * The test that was supposed to catch it could not. client-headers.test.mjs
 * asserted the header equals SDK_VERSION, and the header is built FROM
 * SDK_VERSION: it compared the constant to itself and would pass for any value.
 * That test now reads package.json, so the next bump that misses this line
 * fails the build instead of shipping.
 *
 * The build-time-generation TODO above is still the better answer and still
 * unwritten; a test that fails loudly is enough to stop the drift class in the
 * meantime, and adds no machinery the day before a publish.
 */
export const SDK_VERSION = '2.1.0';

/** ADR 0002 default for `X-ZPL-Client` from this package. */
export const ZPL_SDK_CLIENT_TYPE = 'sdk-typescript' as const;
