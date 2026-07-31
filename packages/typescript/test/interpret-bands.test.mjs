/**
 * Two SDKs, one product, one set of words.
 *
 * AUDIT 2026-07-31: interpretAIN used bands 0.95 / 0.8 / 0.7 / 0.6 / 0.4 / 0.2
 * while the Python SDK used 0.85 / 0.70 / 0.55 / 0.40 / 0.25, and neither
 * matched the engine's ain_status. Measured, same readings, both SDKs:
 *
 *   ain 0.87  TS "Excellent neutrality"  Python "Perfectly Neutral"   engine NEUTRAL
 *   ain 0.75  TS "Good neutrality"       Python "Highly Neutral"      engine MODERATE_BIAS
 *   ain 0.58  TS "Weak neutrality"       Python "Moderately Neutral"  engine SIGNIFICANT_BIAS
 *
 * The same number was described differently depending on which language a team
 * used, and both were softer than the engine that produced it. Python's
 * "Perfectly Neutral" started at 0.85, covering the whole of the engine's
 * NEUTRAL band and most of HIGHLY_NEUTRAL; the engine reserves its top name for
 * 0.96 and above.
 *
 * Both now use the engine's boundaries and identical wording, verified by
 * running them side by side: same string at every reading sampled.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { interpretAIN } from "../dist/utils.js";

/** The engine's bands, from crates/zpl-core/src/ain.rs. */
const BANDS = [
  [0.96, "Certified neutral"],
  [0.9, "Highly neutral"],
  [0.8, "Neutral."],
  [0.6, "Moderate bias"],
  [0.4, "Significant bias"],
  [0, "High bias"],
];

const expected = (ain) => BANDS.find(([lo]) => ain >= lo)[1];

test("every reading is described by its engine band", () => {
  const wrong = [];
  for (let i = 0; i <= 1000; i++) {
    const ain = i / 1000;
    const text = interpretAIN(ain);
    if (!text.startsWith(expected(ain))) {
      wrong.push(`ain ${ain.toFixed(3)}: "${text.split(".")[0]}" for band ${expected(ain)}`);
    }
  }
  assert.deepEqual(
    wrong.slice(0, 5),
    [],
    `${wrong.length} readings described with the wrong band's words`,
  );
});

test("the boundaries are the engine's, not one step off", () => {
  assert.match(interpretAIN(0.96), /^Certified neutral/);
  assert.match(interpretAIN(0.959), /^Highly neutral/);
  assert.match(interpretAIN(0.9), /^Highly neutral/);
  assert.match(interpretAIN(0.899), /^Neutral\./);
  assert.match(interpretAIN(0.8), /^Neutral\./);
  assert.match(interpretAIN(0.799), /^Moderate bias/);
  assert.match(interpretAIN(0.6), /^Moderate bias/);
  assert.match(interpretAIN(0.599), /^Significant bias/);
  assert.match(interpretAIN(0.4), /^Significant bias/);
  assert.match(interpretAIN(0.399), /^High bias/);
});

test("nothing calls a biased reading neutral", () => {
  // The specific softenings that shipped.
  assert.doesNotMatch(interpretAIN(0.87), /Perfect/i, "0.87 is NEUTRAL, not perfect");
  assert.doesNotMatch(interpretAIN(0.75), /Excellent|Good/i, "0.75 is MODERATE_BIAS");
  assert.doesNotMatch(interpretAIN(0.58), /Good|Neutral/i, "0.58 is SIGNIFICANT_BIAS");
});

/**
 * The Python SDK is the other half of this. Read its source when the sibling
 * package is present and check the boundaries match; skip when it is not.
 */
test("the Python SDK uses the same boundaries", async () => {
  let py;
  try {
    py = await readFile(
      new URL("../../python/zeropointlogic/utils.py", import.meta.url),
      "utf-8",
    );
  } catch {
    return;
  }
  const fn = py.slice(py.indexOf("def interpret_ain"));
  const body = fn.slice(0, fn.indexOf("\n\ndef "));
  const bounds = [...body.matchAll(/ain >= ([\d.]+)/g)].map((m) => Number(m[1]));

  assert.deepEqual(
    bounds,
    BANDS.filter(([lo]) => lo > 0).map(([lo]) => lo),
    "the two SDKs use different boundaries again — the same number would be " +
      "described differently depending on the caller's language",
  );
});
