/**
 * The tests read the repo's own files, so how git checks them out is part of
 * the contract.
 *
 * AUDIT 2026-08-02. There was no `.gitattributes`. `core.autocrlf` — the
 * default on a Windows install — rewrites every text file to CRLF on checkout,
 * and a good part of this suite matches repo files against patterns containing
 * `\n`.
 *
 * Measured here: a branch switch rewrote `packages/typescript/README.md` to 662
 * CRLF endings and zero LF, and two README tests went from passing to failing
 * without one character of content changing. 130 tracked text files carried
 * CRLF in the working tree while the index held LF; the sibling repos had 85
 * and 63.
 *
 * That is worse than two red tests. A suite whose result depends on which
 * platform checked the files out cannot be used to decide whether anything is
 * safe to ship, and the person most likely to hit it is a first-time
 * contributor on Windows who concludes the project is broken.
 *
 * This file asserts the two halves of the fix: the rule exists, and the working
 * tree actually obeys it. The second is the one that matters — a
 * `.gitattributes` that is present but not applied looks exactly like one that
 * works, right up until a test reads a file.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFile, readdir, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join, relative, sep } from "node:path";

// test -> packages/typescript -> packages -> repo root. Four levels, and the
// third test below is what catches getting this wrong: it names a file that
// must be inside the walked set, so a REPO pointing at the wrong directory
// fails loudly instead of walking somewhere quiet and passing.
const REPO = dirname(dirname(dirname(dirname(fileURLToPath(import.meta.url)))));

/** Extensions the suite reads as text and matches `\n` against. */
const TEXT = new Set([
  ".md", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".py", ".json",
  ".yml", ".yaml", ".toml", ".txt", ".cfg", ".ini",
]);

/** Directories that are build output or dependencies, not sources. */
const SKIP_DIRS = new Set([
  "node_modules", ".git", "dist", "build", ".venv", "venv",
  "__pycache__", ".pytest_cache", "coverage", ".next", "egg-info",
]);

async function textFiles(dir, out = []) {
  for (const e of await readdir(dir, { withFileTypes: true })) {
    if (e.isDirectory()) {
      if (SKIP_DIRS.has(e.name) || e.name.endsWith(".egg-info")) continue;
      await textFiles(join(dir, e.name), out);
      continue;
    }
    const dot = e.name.lastIndexOf(".");
    if (dot === -1) continue;
    if (TEXT.has(e.name.slice(dot))) out.push(join(dir, e.name));
  }
  return out;
}

test("the repo states a line-ending rule", async () => {
  const path = join(REPO, ".gitattributes");
  let raw;
  try {
    raw = await readFile(path, "utf-8");
  } catch {
    assert.fail(
      "no .gitattributes at the repo root. Without one, a Windows checkout " +
        "rewrites every text file to CRLF and the tests that read those files " +
        "fail for reasons that have nothing to do with the code.",
    );
  }
  // Comments stripped: this file's own reasoning is written in there at length,
  // and a scan that read the prose would pass with the rule deleted.
  const rules = raw
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith("#"))
    .join("\n");

  assert.match(
    rules,
    /^\*\s+text=auto\s+eol=lf$/m,
    `the catch-all normalisation rule is gone. Rules present:\n${rules}`,
  );
});

test("the working tree obeys it", async () => {
  // The assertion that matters. A rule that is declared and not applied reads
  // exactly like one that works.
  const files = await textFiles(REPO);
  assert.ok(
    files.length > 40,
    `only ${files.length} text files found — the walk is not reaching the tree, ` +
      `so the check below would pass over almost nothing`,
  );

  const crlf = [];
  for (const f of files) {
    const buf = await readFile(f);
    if (buf.includes("\r\n")) crlf.push(relative(REPO, f).split(sep).join("/"));
  }

  assert.deepEqual(
    crlf,
    [],
    "these are checked out with CRLF while the suite matches them against \\n. " +
      "Run `git rm --cached -r . && git reset --hard` after adding .gitattributes " +
      "— renormalising the index alone leaves the working tree as it was, which " +
      "is exactly the state that looked fixed and was not.",
  );
});

test("a file this suite actually reads is among the ones checked", async () => {
  // Anchored on a file the suite parses, so the check cannot pass by walking
  // some quiet corner of the tree while the ones that matter go unread.
  const readme = join(REPO, "packages", "typescript", "README.md");
  const st = await stat(readme);
  assert.ok(st.isFile(), "the TypeScript README is gone");

  const files = await textFiles(REPO);
  const rel = relative(REPO, readme).split(sep).join("/");
  assert.ok(
    files.map((f) => relative(REPO, f).split(sep).join("/")).includes(rel),
    `${rel} is not in the set the check above walks, and it is the file whose ` +
      `line endings broke two tests`,
  );

  const buf = await readFile(readme);
  assert.ok(
    !buf.includes("\r\n"),
    "the TypeScript README is checked out with CRLF — the exact state that made " +
      "`/```ts\\n/` stop matching",
  );
});
