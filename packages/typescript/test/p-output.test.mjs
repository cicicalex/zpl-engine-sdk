/**
 * The SDK must surface the measurement, not only the summary derived from it.
 *
 * `p_output` is the engine's actual reading — the balance of the output
 * stream, 0.500 being equilibrium. It arrives on every /compute response and
 * the SDK dropped it in the normaliser, under a note citing IP protection.
 *
 * That reasoning does not survive contact with the wire: the engine's own HTTP
 * response serialises p_output and deviation to every caller holding a key, so
 * both have always been public. Withholding them here hid them from the one
 * audience reading through the SDK while every raw HTTP user had them. The
 * owner's position, asked directly: the calculation stays secret, the numbers
 * it produces do not — a single output coefficient reveals no method.
 *
 * It also matters mathematically. AIN is defined with an absolute value in it,
 * so it cannot say which side of equilibrium a reading sits on: p_output
 * 0.4687 and 0.5313 both come back as AIN 0.9373. For a method whose purpose
 * is finding a stable centre, which way it leans is half the answer.
 *
 * Run after `npm run build`.
 */

import test from "node:test";
import assert from "node:assert/strict";

const { normalizeEngineComputeResult } = await import("../dist/index.js");

const ENGINE_RESPONSE = {
  p_output: 0.4655,
  ain: 0.931,
  ain_status: "HIGHLY_NEUTRAL",
  deviation: 0.0345,
  status: "STABLE",
  samples: 2000,
  d: 9,
  bias: 0.5,
  tokens_used: 2,
  compute_ms: 1.4,
};

test("p_output survives normalisation", () => {
  const r = normalizeEngineComputeResult(ENGINE_RESPONSE);
  assert.equal(r.pOutput, 0.4655, "the engine's own measurement must reach the caller");
});

test("deviation survives normalisation", () => {
  const r = normalizeEngineComputeResult(ENGINE_RESPONSE);
  assert.equal(r.deviation, 0.0345);
});

test("the direction of imbalance is recoverable", () => {
  // The whole point: these two are indistinguishable by AIN alone.
  const low = normalizeEngineComputeResult({ ...ENGINE_RESPONSE, p_output: 0.4687, ain: 0.9373 });
  const high = normalizeEngineComputeResult({ ...ENGINE_RESPONSE, p_output: 0.5313, ain: 0.9373 });

  assert.equal(low.ain, high.ain, "AIN cannot tell these apart — that is the problem");
  assert.notEqual(low.pOutput, high.pOutput, "p_output must tell them apart");
  assert.ok(low.pOutput < 0.5, "one leans toward 0");
  assert.ok(high.pOutput > 0.5, "the other leans toward 1");
});

test("absent fields stay absent rather than becoming zero", () => {
  // An older engine, or a response that genuinely omits them. Reporting 0
  // would claim the output was entirely zeros — a real and very wrong reading.
  const r = normalizeEngineComputeResult({ ain: 0.9, status: "STABLE", tokens_used: 1 });
  assert.equal(r.pOutput, undefined, "a missing measurement must not read as 0.000000");
  assert.equal(r.deviation, undefined);
});

test("everything the normaliser already returned is untouched", () => {
  const r = normalizeEngineComputeResult(ENGINE_RESPONSE);
  assert.equal(r.ain, 0.931);
  assert.equal(r.status, "STABLE");
  assert.equal(r.ainStatus, "HIGHLY_NEUTRAL");
  assert.equal(r.tokensUsed, 2);
  assert.equal(r.computeMs, 1.4);
});
