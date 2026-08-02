/**
 * The shapes this SDK must not hand back to the caller.
 *
 * AUDIT 2026-08-02. The package shipped `redactSecretsInText`, documented "for
 * logs / echoed errors", exported it — and never called it. Measured against an
 * engine that echoed a key back in an error body, which the MCP's own notes
 * record as having happened for real:
 *
 *   error.message  ->  "Invalid request"
 *   error.details  ->  the engine's text verbatim, with a ZPL key, a Bearer
 *                      token and a Stripe secret key all intact
 *
 * The generic `message` is what made it look handled. A consumer logging the
 * error object — the ordinary thing to do — wrote all three into their logs.
 *
 * Its pattern covered ZPL keys only, so even had it been called it would have
 * let the other two through. The CLI and the MCP had drifted apart from each
 * other the same way, found the same day.
 *
 * KEEP THIS CORPUS IDENTICAL to the ones in the CLI and MCP repos. Three copies
 * of a list is a bad shape; three copies that disagree is the bug it replaced.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { redactSecretsInText } from "../dist/index.js";

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const HEX = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6";

/** [label, text containing a secret, the part that must not survive] */
const CORPUS = [
  ["zpl user key", `failed for zpl_u_${HEX}`, `zpl_u_${HEX}`],
  ["zpl user key, wizard prefix", `failed for zpl_u_cli_${HEX}`, `zpl_u_cli_${HEX}`],
  ["zpl service key", `failed for zpl_s_${HEX}`, `zpl_s_${HEX}`],
  ["bearer, long", `Authorization: Bearer ${HEX}${HEX}`, `${HEX}${HEX}`],
  ["bearer, short", "Authorization: Bearer abc123", "abc123"],
  ["bearer, tab separated", `Authorization: Bearer\t${HEX}`, HEX],
  ["openai / anthropic", "key sk-proj-AbCdEf0123456789", "sk-proj-AbCdEf0123456789"],
  ["groq", "key gsk_AbCdEf0123456789", "gsk_AbCdEf0123456789"],
  ["stripe secret, live", "key sk_live_AbCdEf0123456789", "sk_live_AbCdEf0123456789"],
  ["stripe secret, test", "key sk_test_AbCdEf0123456789", "sk_test_AbCdEf0123456789"],
];

test("every shape in the shared corpus is redacted", () => {
  const leaked = [];
  for (const [label, sample, secret] of CORPUS) {
    if (redactSecretsInText(sample).includes(secret)) leaked.push(label);
  }
  assert.deepEqual(
    leaked,
    [],
    "these secret shapes survive redactSecretsInText. The CLI and MCP sets catch them; this one " +
      "is meant to match.",
  );
});

test("the corpus is big enough to be worth running", () => {
  assert.ok(
    CORPUS.length >= 10,
    `the shared corpus is down to ${CORPUS.length} shapes; it had 10`,
  );
  const secrets = new Set(CORPUS.map(([, , s]) => s));
  assert.equal(secrets.size, CORPUS.length, "two corpus rows carry the same secret body");
});

test("ordinary text is left alone", () => {
  // A redactor that redacts everything passes the test above and destroys the
  // error messages it was meant to make safe.
  for (const plain of ["Invalid request", "CERTIFIED_NEUTRAL", "d must be between 3 and 100"]) {
    assert.equal(redactSecretsInText(plain), plain, `mangled ordinary text: ${plain}`);
  }
});

test("the error path actually calls it", async () => {
  // The whole defect: the function existed, was exported, and was skipped.
  // Asserted over the source because it is a wiring fact — a redactor that is
  // never reached passes every test above and protects nobody.
  const src = await readFile(join(ROOT, "src", "client.ts"), "utf-8");
  const code = src.replace(/\/\*[\s\S]*?\*\/|(^|[^:])\/\/[^\n]*/g, (_m, b) => b ?? "");

  // Anchored on the DECLARATION. The first version used
  // indexOf("_parseErrorResponse"), which lands on the call site further up
  // and then extracts the braces of whatever follows it — a block belonging to
  // someone else entirely. It reported the fixed code as unfixed.
  const at = code.search(/private\s+async\s+_parseErrorResponse\b/);
  assert.notEqual(at, -1, "_parseErrorResponse is gone — this guard is checking nothing");

  // Bounded to that method: redactSecretsInText may legitimately appear
  // elsewhere, and the point is that THIS path uses it.
  let i = code.indexOf("{", at);
  let depth = 0;
  let end = code.length;
  for (; i < code.length; i += 1) {
    if (code[i] === "{") depth += 1;
    else if (code[i] === "}") {
      depth -= 1;
      if (depth === 0) {
        end = i + 1;
        break;
      }
    }
  }
  const body = code.slice(at, end);

  assert.match(
    body,
    /\bredactSecretsInText\s*\(/,
    "the engine's error body is returned untouched and ends up on the thrown error as `details`. " +
      "Measured: a key, a Bearer token and a Stripe key all reached the caller intact while " +
      "`message` read a reassuring \"Invalid request\".",
  );
});
