/**
 * A gateway timeout must not be reported as a bot block.
 *
 * AUDIT 2026-07-31, reproduced against production rather than reasoned about:
 *
 *   GET /sweep?d=100&samples=50000
 *     -> 504 after 60.2s, server: cloudflare, content-type: text/html, cf-ray set
 *
 * 60.2s is the engine's own sweep timeout, so the engine did answer — with
 * {"error":"Sweep timeout exceeded 60s","code":504} — and Cloudflare replaced
 * the body with its branded HTML page. Two consequences, both measured:
 *
 *   1. The engine's message never reaches the caller, and any JSON parse fails.
 *   2. Both SDKs then described it wrongly. The page carries Cloudflare
 *      branding, so the snippet check said "Cloudflare blocked the request" —
 *      nothing was blocked; the request was forwarded, ran, and ran out of
 *      clock. And the causes list was fixed text emitted for every status, so
 *      the advice was "use a browser-like User-Agent string" and "wait and
 *      retry". Bot blocking is 403 and rate limiting is 429. Neither produces
 *      a 504, so both suggestions were unreachable for the case at hand.
 *
 * d=100 is Enterprise XL's own ceiling and samples=50000 is the documented
 * maximum, so this was the top of the paid ladder pointing its most expensive
 * customer at the wrong thing.
 *
 * The two SDKs are checked against each other here as well as against the
 * behaviour, because they have drifted apart before: the interpretation bands
 * were different in each language until 2.1.0, and the same reading was
 * described differently depending on which language a team used.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { parseEngineHttpError } from '../dist/errors.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const PY = join(HERE, '..', '..', 'python', 'zeropointlogic', 'http_errors.py');

/** What production actually sent, headers and all. */
function cloudflareTimeout(status = 504) {
  return new Response(
    '<!DOCTYPE html><html lang="en-US"><head>' +
      '<title>zeropointlogic.io | 504: Gateway time-out</title></head>' +
      '<body><h1>Gateway time-out</h1><p>Error code 504</p>' +
      '<p>Ray ID: a23aea752951a63e</p></body></html>',
    {
      status,
      headers: {
        'content-type': 'text/html; charset=UTF-8',
        'cf-ray': 'a23aea752951a63e-FRA',
      },
    },
  );
}

test('a 504 is not described as a block, and does not advise a User-Agent change', async () => {
  const msg = await parseEngineHttpError(cloudflareTimeout(504));

  assert.doesNotMatch(
    msg,
    /User-Agent/i,
    'a gateway timeout still advises changing the User-Agent. Bot blocking is 403; ' +
      'that advice cannot apply to a 504 and sends the caller looking at the wrong thing.',
  );
  assert.doesNotMatch(
    msg,
    /blocked the request/i,
    'a 504 is still called a block. The request was forwarded, ran, and exceeded the ' +
      'clock — nothing blocked it.',
  );
  assert.match(
    msg,
    /did not answer in time|timeout/i,
    'the message no longer says the engine ran out of time, which is the one fact ' +
      'that explains the status.',
  );
  assert.match(
    msg,
    /samples/i,
    'the message no longer names `samples`. It is the lever that scales the work ' +
      'linearly and costs no extra tokens, so it is what the caller should lower first.',
  );
  assert.match(msg, /a23aea752951a63e/, 'the cf-ray must survive for bug reports');
});

test('a genuine block still gets the block advice', async () => {
  // The fix must not swing the other way: a 403 has to keep pointing at bot
  // blocking, or fixing one wrong diagnosis just installs another.
  const res = new Response(
    '<!DOCTYPE html><html><body>Attention Required! | Cloudflare</body></html>',
    { status: 403, headers: { 'content-type': 'text/html', 'cf-ray': 'deadbeef-FRA' } },
  );
  const msg = await parseEngineHttpError(res);

  assert.match(msg, /User-Agent/i, 'a 403 no longer suggests the User-Agent — that is the case where it applies');
  assert.doesNotMatch(msg, /did not answer in time/i, 'a 403 is now described as a timeout');
});

test('522 and 524 are treated as timeouts too', async () => {
  // Cloudflare uses 522 for a connection timeout and 524 when the origin
  // accepted the request and never finished. Both mean the same thing to a
  // caller as 504 does, and a fix that only knew 504 would leave the two
  // statuses most specific to a slow origin advising a User-Agent change.
  for (const status of [522, 524]) {
    const msg = await parseEngineHttpError(cloudflareTimeout(status));
    assert.doesNotMatch(msg, /User-Agent/i, `${status} still advises a User-Agent change`);
    assert.match(msg, /did not answer in time|timeout/i, `${status} is not described as a timeout`);
  }
});

test('the Python SDK says the same thing, and has not drifted', async () => {
  const py = await readFile(PY, 'utf-8');

  assert.match(
    py,
    /timed_out\s*=\s*status\s+in\s*\(504,\s*522,\s*524\)/,
    'the Python SDK no longer branches on the timeout statuses, so the two languages ' +
      'now describe the same production failure differently.',
  );
  assert.match(
    py,
    /did not answer in time/,
    'the Python snippet no longer states that the engine ran out of time',
  );
  assert.match(
    py,
    /Lower `samples` first/,
    'the Python advice no longer names `samples` as the first lever',
  );
});
