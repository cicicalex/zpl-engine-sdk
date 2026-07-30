import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeEngineComputeResult, redactSecretsInText } from '../dist/utils.js';

// AUDIT 2026-05-13 (B2 + D4):
//   - pOutput + deviation removed from the public ComputeResult shape
//     to plug what was believed to be an IP leak.
//
// AUDIT 2026-07-30: reversed. The engine's own HTTP response serialises
// both to every caller holding a key, so neither was ever secret — they
// were hidden only from people reading through a client. The owner's
// position, asked directly: the calculation stays secret, the numbers it
// produces do not. The assertions below pinned the old decision and are
// updated rather than deleted, so the reversal shows in the history
// instead of looking like drift.
//   - tokensRemaining is now Optional — only set when the engine
//     actually returns it. Absent → undefined (caller renders "n/a"),
//     never the misleading "0 left" scare message.
test('normalizeEngineComputeResult maps snake_case engine JSON', () => {
  const r = normalizeEngineComputeResult({
    ain: 0.82,
    p_output: 0.51,
    deviation: 0.02,
    status: 'STABLE',
    ain_status: 'NEUTRAL',
    samples: 1000,
    tokens_used: 2,
    compute_ms: 14.5,
  });
  assert.equal(r.ain, 0.82);
  assert.equal(r.status, 'STABLE');
  assert.equal(r.ainStatus, 'NEUTRAL');
  assert.equal(r.tokensUsed, 2);
  // tokens_remaining absent from input → undefined on result.
  assert.equal(r.tokensRemaining, undefined);
  assert.equal(r.computeMs, 14.5);
  // These reach the caller now. pOutput is the engine's measurement — output
  // balance, 0.500 being equilibrium — and ain is derived from it through an
  // absolute value, so it cannot express which side of equilibrium a reading
  // sits on.
  assert.equal(r.pOutput, 0.51);
  assert.equal(r.deviation, 0.02);
});

test('normalizeEngineComputeResult forwards tokensRemaining when engine returns it', () => {
  const r = normalizeEngineComputeResult({
    ain: 0.91,
    status: 'STABLE',
    tokens_used: 1,
    tokens_remaining: 4999,
  });
  assert.equal(r.tokensRemaining, 4999);
});

// The two status enums are different fields with different values.
// Pre-fix `INHIBITED_HIGH` was not in the accepted list and got rewritten
// to `STABLE` — the SDK reported the opposite of the engine.
test('normalizeEngineComputeResult keeps the inhibited stability regimes', () => {
  for (const s of ['STABLE', 'ACTIVE', 'INHIBITED_HIGH', 'INHIBITED_LOW']) {
    const r = normalizeEngineComputeResult({ ain: 0.5, status: s, tokens_used: 1 });
    assert.equal(r.status, s);
  }
  // Plain `INHIBITED` is not a valid value; it must not pass through.
  const bad = normalizeEngineComputeResult({ ain: 0.5, status: 'INHIBITED', tokens_used: 1 });
  assert.equal(bad.status, 'STABLE');
  // `status` values are not accepted as `ain_status` and vice versa.
  const mixed = normalizeEngineComputeResult({
    ain: 0.5,
    status: 'CERTIFIED_NEUTRAL',
    ain_status: 'STABLE',
    tokens_used: 1,
  });
  assert.equal(mixed.status, 'STABLE');
  assert.equal(mixed.ainStatus, undefined);
});

test('redactSecretsInText masks zpl keys', () => {
  const s = redactSecretsInText('failed zpl_s_abc123456789012345678901234567890');
  assert.ok(s.includes('zpl_[REDACTED]'));
  assert.ok(!s.includes('abc123456789012345678901234567890'));
});
