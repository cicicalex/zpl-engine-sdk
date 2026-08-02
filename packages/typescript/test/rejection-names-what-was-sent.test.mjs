/**
 * A rejection must describe the matrix the caller actually sent.
 *
 * AUDIT 2026-08-02. Both row-count branches of validateMatrix printed the row
 * count twice — `${size}x${size}` — so for anything not already square the
 * second number was invented. Measured through the BUILT package, which is what
 * a customer installs:
 *
 *   2 rows x 5 columns   -> "got 2x2"
 *   1 row  x 4 columns   -> "got 1x1"
 *   150 rows x 7 columns -> "got 150x150"
 *
 * The engine had the same defect and was fixed the same day. It matters more
 * here, because this runs BEFORE anything is sent: the engine's corrected
 * message never reaches the caller, so what a customer reads is what this
 * throws. Someone who sent seven columns and is told they sent 150 goes looking
 * for a bug that is not there.
 *
 * The squareness branch never had the problem — it names both numbers it saw —
 * and is pinned so a change to its siblings does not take it along.
 *
 * Behavioural rather than a source scan: what matters is the string a customer
 * reads, and asserting on it cannot drift from the template the way a pattern
 * match over the source can.
 */

import test from "node:test";
import assert from "node:assert/strict";

// The BUILT package, the way every other test here reads it and the way a
// customer installs it. A source import would prove nothing about what ships.
import { validateMatrix } from "../dist/index.js";

/** `rows` x `cols`, alternating bits. Not square unless the two match. */
const grid = (rows, cols) =>
  Array.from({ length: rows }, (_, i) => Array.from({ length: cols }, (_, j) => (i + j) % 2));

function reject(rows, cols) {
  try {
    validateMatrix(grid(rows, cols));
  } catch (e) {
    return e.message;
  }
  assert.fail(`${rows}x${cols} was accepted; this test needs an input that is refused`);
}

test("a matrix below the minimum is told its real width", () => {
  for (const [rows, cols] of [
    [2, 3],
    [2, 5],
    [1, 4],
  ]) {
    const msg = reject(rows, cols);
    assert.ok(
      msg.includes(String(cols)),
      `the refusal for a ${rows}x${cols} matrix never mentions its ${cols} columns: ${msg}`,
    );
    // The shape that was there: the row count printed as both dimensions.
    const fabricated = `${rows}x${rows}`;
    assert.ok(
      !msg.includes(fabricated),
      `the refusal reports '${fabricated}' for a matrix that is ${rows}x${cols}. The second ` +
        `number is the row count printed twice, not anything the caller sent: ${msg}`,
    );
  }
});

test("an oversized matrix is told its real width too", () => {
  // The same template, the same defect, in the branch nobody exercised.
  for (const [rows, cols] of [
    [101, 3],
    [150, 7],
  ]) {
    const msg = reject(rows, cols);
    assert.ok(
      msg.includes(`${cols} column`),
      `the refusal for a ${rows}x${cols} matrix never mentions its ${cols} columns: ${msg}`,
    );
    const fabricated = `${rows}x${rows}`;
    assert.ok(
      !msg.includes(fabricated),
      `the refusal reports '${fabricated}' for a matrix that is ${rows}x${cols}: ${msg}`,
    );
  }
});

test("the squareness refusal still names both numbers", () => {
  // This branch was already correct. Pinned so a change to its siblings does not
  // take it with them.
  const msg = reject(5, 3);
  assert.ok(
    msg.includes("5") && msg.includes("3"),
    `the squareness refusal no longer names both the row count and the offending width: ${msg}`,
  );
});

test("the refusal says the same thing the engine would", () => {
  // Three surfaces answer this question — the engine, this package, and the
  // Python package — and a customer who moves between them should not be told
  // two different stories about the same matrix. The engine's wording, fixed the
  // same day, is the one being matched.
  const msg = reject(2, 5);
  assert.match(
    msg,
    /got 2 row\(s\); row 0 has 5 column\(s\)/,
    `this package no longer phrases the refusal the way the engine does: ${msg}`,
  );
});

test("a valid matrix is still accepted", () => {
  // A refusal that describes the input perfectly and refuses everything is not
  // an improvement.
  for (const n of [3, 9, 100]) {
    assert.doesNotThrow(
      () => validateMatrix(grid(n, n)),
      `a valid ${n}x${n} matrix was refused`,
    );
  }
});

test("a matrix whose first row is not an array is still refused, without throwing", () => {
  // The width is read from row 0 before rows have been checked, so row 0 may be
  // anything at all. It must not take the validator down with it.
  for (const bad of [[1, 2], ["nope", "nope", "nope"], [null, null, null]]) {
    assert.throws(
      () => validateMatrix(bad),
      (e) => e?.name !== "TypeError",
      `a malformed matrix produced a TypeError instead of a refusal: ${JSON.stringify(bad)}`,
    );
  }
});
