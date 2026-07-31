/**
 * The two most opposite matrices must not arrive as the same object.
 *
 * AUDIT 2026-07-31: the engine was swept over 3..=100. At every even dimension
 * the four family bits for an all-zeros matrix are identical to those for an
 * all-ones matrix — 49 of the 49 even dimensions, and none of the 49 odd ones.
 * Every paid ceiling except Pro's 25 is even: 16, 32, 48, 64, 100.
 *
 * The engine now returns input_ones / cells / degenerate, which are the
 * caller's own matrix counted back to them. These tests pin the mapping and
 * the trap inside it: 0 is a real count, not a missing value. Defaulting an
 * absent field to 0 would make an old engine's silence indistinguishable from
 * an all-zeros matrix — the same class of collapse being fixed.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { ZPLClient } from "../dist/index.js";

/** A client whose transport is replaced, so no network is involved. */
function clientReturning(payload) {
  const c = new ZPLClient({ apiKey: "zpl_u_" + "a".repeat(48) });
  c._request = async () => payload;
  return c;
}

const FAMILIES = [0, 1, 2, 3].map((family) => ({ family, bit: 0, tie_broken: false }));

const base = (over = {}) => ({
  n: 16,
  families: FAMILIES,
  ones: 0,
  unanimous: true,
  tokens_used: 5,
  ...over,
});

const matrix16 = Array.from({ length: 16 }, () => Array(16).fill(0));

test("an all-zeros and an all-ones matrix do not produce the same result", async () => {
  const zeros = await clientReturning(
    base({ input_ones: 0, cells: 256, degenerate: true }),
  ).analyze({ matrix: matrix16 });
  const ones = await clientReturning(
    base({ input_ones: 256, cells: 256, degenerate: true }),
  ).analyze({ matrix: matrix16 });

  // The verdicts are identical on purpose — that is the case being defended.
  assert.deepEqual(zeros.families, ones.families, "fixture must share a verdict");
  assert.notDeepEqual(
    zeros,
    ones,
    "identical results for the two most opposite inputs a caller can send",
  );
  assert.equal(zeros.inputOnes, 0);
  assert.equal(ones.inputOnes, 256);
});

test("zero is a count, not a missing value", async () => {
  const r = await clientReturning(
    base({ input_ones: 0, cells: 256, degenerate: true }),
  ).analyze({ matrix: matrix16 });

  assert.equal(r.inputOnes, 0, "an all-zeros matrix must report 0");
  assert.notEqual(r.inputOnes, undefined, "0 must not be confused with absent");
  assert.equal(r.degenerate, true);
  assert.equal(r.cells, 256);
});

test("an older engine's silence stays undefined", async () => {
  const r = await clientReturning(base()).analyze({ matrix: matrix16 });

  assert.equal(r.inputOnes, undefined, "absent must not be coerced to 0");
  assert.equal(r.cells, undefined);
  assert.equal(r.degenerate, undefined);
  // The fields that always existed must still map.
  assert.equal(r.n, 16);
  assert.equal(r.ones, 0);
  assert.equal(r.unanimous, true);
  assert.equal(r.tokensUsed, 5);
});

test("a structured matrix is not reported degenerate", async () => {
  const r = await clientReturning(
    base({ input_ones: 128, cells: 256, degenerate: false }),
  ).analyze({ matrix: matrix16 });

  assert.equal(r.degenerate, false);
  assert.ok(r.inputOnes > 0 && r.inputOnes < r.cells);
});
