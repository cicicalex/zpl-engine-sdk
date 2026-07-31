/**
 * Do not tell a customer to buy something that does not exist.
 *
 * AUDIT 2026-07-31: both SDKs refused a matrix above 100x100 with
 *
 *     "The engine rejects dimension > 100; upgrade plan if you need higher d."
 *
 * No amount of money follows that advice. 100 is BinaryMatrix::MAX_N, a hard
 * engine constant, and the request is refused before any plan is consulted. The
 * most expensive plan, Enterprise XL at $999/mo, grants exactly max_d 100 —
 * there is nothing above it to buy at any price.
 *
 * The sentence also conflated two different limits, which is why it reads
 * plausibly. Below 100 the per-plan ceiling — 9 / 16 / 25 / 32 / 48 / 64 / 100
 * — is real, and upgrading does raise it. The engine reports that case itself
 * with "Dimension X exceeds plan limit of Y". So the advice was correct for a
 * situation this message never fires in, and wrong for the only one it does.
 *
 * Both SDKs are checked here because they carried the identical sentence and
 * were fixed together; the two have drifted apart before.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { validateMatrix } from '../dist/utils.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const PY_UTILS = join(HERE, '..', '..', 'python', 'zeropointlogic', 'utils.py');
const ENGINE_MATRIX = 'C:/Proiecte/zpl-engine-source/crates/zpl-core/src/matrix.rs';

const square = (n) =>
  Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => (i + j) % 2));

test('an over-limit matrix is not answered with an upgrade suggestion', () => {
  let message = '';
  try {
    validateMatrix(square(101));
    assert.fail('a 101x101 matrix was accepted — the engine rejects it');
  } catch (e) {
    message = e.message;
  }

  assert.doesNotMatch(
    message,
    /upgrade/i,
    'refusing a matrix above the engine ceiling still suggests upgrading. No plan ' +
      'accepts more than 100 — Enterprise XL at $999/mo grants exactly 100 — so this ' +
      'sends a paying customer to buy something that does not exist.',
  );
  assert.match(
    message,
    /hard maximum|not a plan limit/i,
    'the message no longer says that 100 is the engine\'s own limit rather than the ' +
      "caller's plan, which is the fact that makes the refusal actionable",
  );
});

test('the ceiling quoted matches the engine constant', async () => {
  // The number is written into both messages, so it can go stale silently.
  let rust;
  try {
    rust = await readFile(ENGINE_MATRIX, 'utf-8');
  } catch {
    return; // engine repo not checked out beside this one
  }

  const m = rust.match(/const MAX_N:\s*usize\s*=\s*(\d+)/);
  assert.ok(m, 'could not read MAX_N from the engine');
  const maxN = Number(m[1]);

  // The largest matrix the engine takes must still pass validation, and one
  // cell larger must not. Anything else means the SDK and the engine disagree
  // about where the wall is.
  assert.doesNotThrow(
    () => validateMatrix(square(maxN)),
    `a ${maxN}x${maxN} matrix is refused locally, but the engine accepts it`,
  );
  assert.throws(
    () => validateMatrix(square(maxN + 1)),
    `a ${maxN + 1}x${maxN + 1} matrix passes validation, but the engine returns 400`,
  );
});

test('the Python SDK gives the same answer', async () => {
  const py = await readFile(PY_UTILS, 'utf-8');

  // Strip comments: the audit note above the fix quotes the old sentence, and a
  // raw scan would find the word "upgrade" in it and report the bug unfixed —
  // or, worse, find the new wording in a comment and report it fixed when it is
  // not.
  const code = py.replace(/^\s*#.*$/gm, '');

  assert.doesNotMatch(
    code,
    /upgrade plan if you need higher d/i,
    'the Python SDK still suggests upgrading past a ceiling no plan exceeds',
  );
  assert.match(
    code,
    /hard maximum, not a plan limit/,
    'the Python SDK no longer explains that 100 is the engine\'s limit, so the two ' +
      'languages now answer the same question differently',
  );
});
