/**
 * Contract guards for both SDK packages.
 *
 * Why this file exists:
 *   MCP, CLI and the website each guard their own source against the
 *   numeric contract. The SDK was the last package without any such check,
 *   and it is the one that ships its `src` directory inside the npm
 *   tarball — whatever is written here is readable by anyone who installs
 *   it, not just by whoever opens the repo.
 *
 *   It is also the package where the status enum was found conflating two
 *   different engine fields, silently rewriting stability regimes into
 *   STABLE and destroying information the engine had actually returned.
 *   That class of mistake is exactly what a guard cannot catch and a type
 *   can — so the guards below cover the textual claims, and the split
 *   AINStatus / StabilityStatus types cover the structural one.
 *
 * Scope: both packages/typescript/src and packages/python/zeropointlogic,
 * because a claim is no less public for being written in Python.
 *
 * Comment lines are skipped. Every rule here is also *described* in a
 * docstring in one of those trees, and a guard that flags its own
 * documentation is a guard someone deletes.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readdir, readFile, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

// test/ -> typescript/ -> packages/ -> repo root
const REPO = dirname(dirname(dirname(dirname(fileURLToPath(import.meta.url)))));
const TREES = [
  join(REPO, "packages", "typescript", "src"),
  join(REPO, "packages", "python", "zeropointlogic"),
];

/** Integer rounding of an AIN value, whatever the receiver is called. */
const INT_ROUNDING =
  /(?:Math\.round|round)\([^)]*\bain\s*\*\s*100\s*\)/i;

/** The fictional 0.1-99.9 range. Bounded gap — the real wording had 23 chars. */
const FALSE_RANGE = /0\.1\b[^\n]{0,30}?\b99\.9/;

/** Accuracy / match percentages with no measurement behind them. */
const UNSUPPORTED_ACCURACY =
  /\b\d{1,3}\s*(?:-|–|to)?\s*\d{0,3}\s*%\s*(?:accuracy|match|correct|agreement)/i;

/** Bare INHIBITED — the engine emits INHIBITED_HIGH / INHIBITED_LOW only. */
const BARE_INHIBITED = /["'`]INHIBITED["'`]/;

function isComment(line) {
  const t = line.trim();
  return (
    t.startsWith("*") ||
    t.startsWith("//") ||
    t.startsWith("/*") ||
    t.startsWith("#") ||
    t.startsWith('"""') ||
    t.startsWith("'''")
  );
}

async function sourceFiles(dir) {
  let entries;
  try {
    entries = await readdir(dir, { withFileTypes: true });
  } catch {
    return []; // tree absent in this checkout — nothing to guard
  }
  const out = [];
  for (const entry of entries) {
    const p = join(dir, entry.name);
    if (entry.isDirectory()) out.push(...(await sourceFiles(p)));
    else if (/\.(ts|py)$/.test(entry.name)) out.push(p);
  }
  return out;
}

/**
 * Python docstrings span lines, and the rule this file enforces is spelled
 * out inside one: models.py documents "never round(ain * 100)" as guidance.
 * A check that only skipped lines *starting* with a triple quote read the
 * body of that docstring as a violation.
 *
 * This is the fourth time in one day that documentation of a rule has been
 * mistaken for a breach of it. Tracking the block state is the fix; the
 * pattern is worth remembering.
 */
function stripDocstrings(lines, isPython) {
  if (!isPython) return lines.map((l) => (isComment(l) ? "" : l));
  let inside = false;
  return lines.map((line) => {
    const fences = (line.match(/"""|'''/g) ?? []).length;
    const wasInside = inside;
    if (fences % 2 === 1) inside = !inside;
    // Blank out the whole line when it opens, closes, or sits inside a block.
    if (wasInside || fences > 0 || isComment(line)) return "";
    return line;
  });
}

async function scan(pattern) {
  const offenders = [];
  for (const tree of TREES) {
    for (const file of await sourceFiles(tree)) {
      const rel = file.slice(REPO.length + 1);
      const raw = (await readFile(file, "utf-8")).split(/\r?\n/);
      const lines = stripDocstrings(raw, file.endsWith(".py"));
      lines.forEach((line, i) => {
        if (!line) return;
        if (pattern.test(line)) offenders.push(`${rel}:${i + 1}: ${line.trim()}`);
      });
    }
  }
  return offenders;
}

test("both SDK trees are present", async () => {
  const found = [];
  for (const tree of TREES) {
    try {
      if ((await stat(tree)).isDirectory()) found.push(tree);
    } catch {
      /* absent */
    }
  }
  assert.ok(
    found.length > 0,
    "no SDK source tree found — the guards below would pass vacuously",
  );
});

test("no SDK code rounds an AIN value to a whole percent", async () => {
  const offenders = await scan(INT_ROUNDING);
  assert.deepEqual(offenders, [], `AIN precision lost:\n${offenders.join("\n")}`);
});

test("no SDK code advertises the fictional 0.1-99.9 range", async () => {
  const offenders = await scan(FALSE_RANGE);
  assert.deepEqual(offenders, [], `false range claim:\n${offenders.join("\n")}`);
});

test("no SDK code quotes an accuracy or match percentage", async () => {
  const offenders = await scan(UNSUPPORTED_ACCURACY);
  assert.deepEqual(offenders, [], `unsupported claim:\n${offenders.join("\n")}`);
});

test("no SDK code uses a bare INHIBITED status", async () => {
  const offenders = await scan(BARE_INHIBITED);
  assert.deepEqual(
    offenders,
    [],
    `INHIBITED is not an engine value — use INHIBITED_HIGH / INHIBITED_LOW:\n${offenders.join("\n")}`,
  );
});

test("each guard matches what it is meant to catch", () => {
  assert.ok(INT_ROUNDING.test("return Math.round(result.ain * 100);"), "typescript form");
  assert.ok(INT_ROUNDING.test("pct = round(snap.ain * 100)"), "python form, and the receiver name that survived every earlier sweep");
  assert.ok(FALSE_RANGE.test("Score: **0.1** (extreme bias) to **99.9**"), "markdown wording");
  assert.ok(UNSUPPORTED_ACCURACY.test("~93% match with human intuition"), "accuracy claim");
  assert.ok(BARE_INHIBITED.test('status == "INHIBITED"'), "bare status");
});

test("guards stay quiet on legitimate code", () => {
  assert.ok(!INT_ROUNDING.test("const pct = ainPercent(result.ain);"), "helper call");
  assert.ok(!INT_ROUNDING.test("round(usage.percent_used * 100)"), "a percentage that is not AIN");
  assert.ok(!UNSUPPORTED_ACCURACY.test("100% of the monthly quota"), "quota wording");
  assert.ok(!BARE_INHIBITED.test('status == "INHIBITED_LOW"'), "the real value passes");
});

test("python docstrings are not read as code", () => {
  const src = [
    'def fmt(ain):',
    '    """Display helper.',
    '    Use f-string formatting; never round(ain * 100), which drops precision.',
    '    """',
    '    return f"{ain * 100:.2f}"',
  ];
  const stripped = stripDocstrings(src, true).join("\n");
  assert.ok(
    !INT_ROUNDING.test(stripped),
    "the rule stated inside a docstring must not count as a breach of it",
  );
});
