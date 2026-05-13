import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeEngineComputeResult, redactSecretsInText } from '../dist/utils.js';

// AUDIT 2026-05-13 (B2 + D4):
//   - pOutput + deviation removed from the public ComputeResult shape
//     to plug an IP leak (engine internals must not appear in the SDK
//     types). They still arrive in the wire response, the normaliser
//     just drops them.
//   - tokensRemaining is now Optional — only set when the engine
//     actually returns it. Absent → undefined (caller renders "n/a"),
//     never the misleading "0 left" scare message.
test('normalizeEngineComputeResult maps snake_case engine JSON', () => {
  const r = normalizeEngineComputeResult({
    ain: 0.82,
    p_output: 0.51,    // still in wire response, dropped by normaliser
    deviation: 0.02,   // same
    status: 'STABLE',
    ain_status: 'STABLE',
    samples: 1000,
    tokens_used: 2,
    compute_ms: 14.5,
  });
  assert.equal(r.ain, 0.82);
  assert.equal(r.status, 'STABLE');
  assert.equal(r.ainStatus, 'STABLE');
  assert.equal(r.tokensUsed, 2);
  // tokens_remaining absent from input → undefined on result.
  assert.equal(r.tokensRemaining, undefined);
  assert.equal(r.computeMs, 14.5);
  // IP leak guards: pOutput + deviation must NOT be on the result.
  assert.equal(r.pOutput, undefined);
  assert.equal(r.deviation, undefined);
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

test('redactSecretsInText masks zpl keys', () => {
  const s = redactSecretsInText('failed zpl_s_abc123456789012345678901234567890');
  assert.ok(s.includes('zpl_[REDACTED]'));
  assert.ok(!s.includes('abc123456789012345678901234567890'));
});
