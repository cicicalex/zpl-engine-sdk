/**
 * Every matrix in the published documentation must be one the SDK accepts.
 *
 * Why this file exists:
 *   Both packages led with `[[0,1],[1,0]]`. The SDK's own validator rejects
 *   it — "Matrix must be at least 3x3 (got 2x2). The engine requires
 *   dimension >= 3." It appeared in the TypeScript class JSDoc (so it is what
 *   an editor shows on hover), in both QUICKSTART files, and in both README
 *   files, which are the pages npm and PyPI render as the landing page.
 *
 *   The first thing anyone did with this SDK was copy that example and get an
 *   exception. The package had 512 downloads a month and no working users.
 *
 *   A grep is not enough to keep it fixed: writing this guard turned up an
 *   invalid matrix in a shape the grep pattern did not match. The check below
 *   parses every binary matrix literal it can find and applies the real rule.
 *
 * Deliberate exemptions, both correct as they stand:
 *   - `normalize_matrix(...)` demos, whose whole point is mapping arbitrary
 *     numbers onto 0/1. Size is irrelevant there and never reaches a
 *     validator.
 *   - tests/, where 2x2 matrices are the negative cases asserting that a
 *     too-small matrix IS rejected. Weakening those would be the opposite of
 *     the fix.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

// test/ -> typescript/ -> packages/
const PACKAGES = dirname(dirname(dirname(fileURLToPath(import.meta.url))));

const DOCS = [
  "typescript/QUICKSTART.md",
  "typescript/README.md",
  "typescript/SDK_SUMMARY.md",
  "typescript/src/client.ts",
  "python/README.md",
  "python/QUICKSTART.md",
  "python/COMPLETION_REPORT.md",
  "python/SDK_OVERVIEW.md",
];

/** A binary matrix literal: [[0,1,...],[...]] with only 0 and 1 inside. */
const MATRIX_LITERAL =
  /\[\s*\[\s*[01]\s*(?:,\s*[01]\s*)*\](?:\s*,\s*\[\s*[01]\s*(?:,\s*[01]\s*)*\])*\s*\]/g;

/** The engine's rule, per ZPL_CONTRACT.md: square, 3..100, binary cells. */
function contractViolation(m) {
  if (!Array.isArray(m) || !Array.isArray(m[0])) return null; // not a matrix
  const n = m.length;
  if (n < 3) return `${n}x${n} is below the minimum dimension of 3`;
  if (n > 100) return `${n}x${n} is above the maximum dimension of 100`;
  for (const row of m) {
    if (!Array.isArray(row) || row.length !== n) {
      return `not square: ${n} rows, a row of length ${row?.length}`;
    }
  }
  return null;
}

async function docMatrices() {
  const found = [];
  for (const rel of DOCS) {
    const text = await readFile(join(PACKAGES, rel), "utf-8");
    text.split(/\r?\n/).forEach((line, i) => {
      // See the exemption note at the top of this file.
      if (line.includes("normalize_matrix")) return;
      for (const literal of line.match(MATRIX_LITERAL) ?? []) {
        let parsed;
        try {
          parsed = JSON.parse(literal);
        } catch {
          continue;
        }
        if (Array.isArray(parsed[0])) {
          found.push({ where: `${rel}:${i + 1}`, literal, parsed });
        }
      }
    });
  }
  return found;
}

test("the documentation actually contains matrix examples", async () => {
  const found = await docMatrices();
  assert.ok(
    found.length >= 10,
    `only ${found.length} matrix examples found across the docs — either the ` +
      `files moved or the pattern stopped matching, and the check below ` +
      `would pass without examining anything`,
  );
});

test("every documented matrix is one the SDK will accept", async () => {
  const offenders = [];
  for (const { where, literal, parsed } of await docMatrices()) {
    const why = contractViolation(parsed);
    if (why) offenders.push(`${where}: ${literal} — ${why}`);
  }
  assert.deepEqual(
    offenders,
    [],
    `documented examples that the SDK's own validator rejects:\n${offenders.join("\n")}`,
  );
});

test("the rule itself catches what it is meant to catch", () => {
  assert.ok(contractViolation([[0, 1], [1, 0]]), "the 2x2 that shipped must fail");
  assert.ok(contractViolation([[0, 1, 0], [1, 0, 1]]), "non-square must fail");
  assert.equal(contractViolation([[0, 1, 0], [1, 0, 1], [0, 1, 0]]), null, "a valid 3x3 passes");
});
