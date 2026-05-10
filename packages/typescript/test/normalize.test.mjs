import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeEngineComputeResult, redactSecretsInText } from '../dist/utils.js';

test('normalizeEngineComputeResult maps snake_case engine JSON', () => {
  const r = normalizeEngineComputeResult({
    ain: 0.82,
    p_output: 0.51,
    deviation: 0.02,
    status: 'STABLE',
    ain_status: 'STABLE',
    samples: 1000,
    tokens_used: 2,
    compute_ms: 14.5,
  });
  assert.equal(r.ain, 0.82);
  assert.equal(r.pOutput, 0.51);
  assert.equal(r.deviation, 0.02);
  assert.equal(r.status, 'STABLE');
  assert.equal(r.ainStatus, 'STABLE');
  assert.equal(r.tokensUsed, 2);
  assert.equal(r.tokensRemaining, 0);
  assert.equal(r.computeMs, 14.5);
});

test('redactSecretsInText masks zpl keys', () => {
  const s = redactSecretsInText('failed zpl_s_abc123456789012345678901234567890');
  assert.ok(s.includes('zpl_[REDACTED]'));
  assert.ok(!s.includes('abc123456789012345678901234567890'));
});
