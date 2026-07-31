/**
 * The README must explain p_output, and its example must be real code.
 *
 * AUDIT 2026-07-31: p_output was restored to both SDKs on 2026-05-13 after
 * being stripped as "IP protection", and both type definitions document it
 * carefully — in code comments. Neither README mentioned it. The Python one
 * contained the string `p_output` exactly once, inside a raw JSON dump with no
 * explanation.
 *
 * So the one fact a caller most needs before building on `ain` — that `ain` is
 * derived through an absolute value and therefore cannot say which side of
 * equilibrium a reading sits on — lived only where the people who already knew
 * it would look. Same shape as the accuracy claim scrubbed from src/ and left
 * in package.json, and the README test count that went stale unguarded: the
 * surface users read had no guard on it.
 *
 * The example is checked, not just its presence. Writing it, I got the call
 * shape wrong — `compute({ d, bias })`, which is the engine's HTTP contract,
 * not this SDK's, whose compute takes a matrix. `tsc --strict` caught it. A
 * README example that does not compile is worse than none, because it is
 * copied.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));

async function readme() {
  return readFile(join(ROOT, "README.md"), "utf-8");
}

test("the README explains what p_output is", async () => {
  const md = await readme();
  assert.match(md, /###\s+p_output/, "no p_output section");
  assert.match(
    md,
    /0\.500 is equilibrium/i,
    "the section must say what 0.500 means — that is the whole point of it",
  );
});

test("the README states the limitation that makes p_output necessary", async () => {
  const md = await readme();
  const section = md.slice(md.indexOf("### p_output"), md.indexOf("### Binary Matrix"));
  assert.ok(section.length > 200, "the section is too short to have explained anything");

  assert.match(
    section,
    /cannot tell you which side/i,
    "must state that ain cannot express direction",
  );
  // The worked pair is the proof, and it is the part most likely to be trimmed.
  assert.match(section, /0\.4687/, "the worked example pair must survive edits");
  assert.match(section, /0\.5313/, "the worked example pair must survive edits");
  assert.match(
    section,
    /0\.9373/,
    "both p_output values must be shown mapping to the same AIN",
  );
});

test("the example uses this SDK's actual compute signature", async () => {
  const md = await readme();
  const section = md.slice(md.indexOf("### p_output"), md.indexOf("### Binary Matrix"));
  const code = section.match(/```ts\n([\s\S]*?)```/);
  assert.ok(code, "the section must carry a runnable example");

  assert.match(
    code[1],
    /compute\(\{\s*[\s\S]*?matrix:/,
    "compute() takes a matrix in this SDK — `{ d, bias }` is the engine's HTTP " +
      "contract and does not type-check here",
  );
  assert.doesNotMatch(
    code[1],
    /compute\(\{\s*d:/,
    "the engine's HTTP shape must not be presented as the SDK's",
  );
});

test("the example guards the optional field before doing arithmetic on it", async () => {
  const md = await readme();
  const section = md.slice(md.indexOf("### p_output"), md.indexOf("### Binary Matrix"));
  const code = section.match(/```ts\n([\s\S]*?)```/)[1];

  const guardAt = code.search(/pOutput\s*===\s*undefined/);
  const mathAt = code.search(/pOutput\s*-\s*0\.5/);
  assert.ok(guardAt !== -1, "pOutput is optional — the example must check it");
  assert.ok(mathAt !== -1, "the example must show the signed offset");
  assert.ok(
    guardAt < mathAt,
    "the check has to come before the subtraction, or the example teaches the bug " +
      "the paragraph below it warns about",
  );
});

test("the README warns against defaulting a missing reading to zero", async () => {
  const md = await readme();
  const section = md.slice(md.indexOf("### p_output"), md.indexOf("### Binary Matrix"));
  assert.match(
    section,
    /not "missing"|is not "missing"/i,
    "a pOutput of 0 is the most extreme reading, not an absent one — saying so is " +
      "what stops `?? 0` appearing in callers",
  );
});
