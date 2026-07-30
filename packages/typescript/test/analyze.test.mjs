/**
 * The SDK must send the caller's matrix, not a summary of it.
 *
 * `compute(matrix)` never transmits the matrix. It reduces it to a dimension
 * and a density of ones, sends those two numbers, and the engine generates
 * fresh random matrices at that density and reports on those. So two entirely
 * different inputs with the same density receive the same answer, and nothing
 * in the response says the caller's data was never looked at.
 *
 * That behaviour is not changed here — existing callers keep exactly what they
 * had. `analyze()` is added alongside it and posts the matrix itself to
 * /analyze, which runs the method over that matrix and reports what each
 * operator family concluded.
 *
 * These tests assert the distinction at the wire level: what URL was called
 * and what bytes were in the body. A test that only checked the return value
 * could not tell the two apart, which is how this went unnoticed.
 *
 * Run after `npm run build`.
 */

import test from 'node:test';
import assert from 'node:assert/strict';

// The client fires a one-shot adoption heartbeat from its constructor, which
// would otherwise show up in the recorded calls and make the counts below
// depend on which test ran first. Disabled before the module is imported.
process.env.ZPL_SKIP_HEARTBEAT = '1';

const { ZPLClient } = await import('../dist/index.js');

const KEY = 'zpl_u_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6';

const CHECKERBOARD_5 = [
  [0, 1, 0, 1, 0],
  [1, 0, 1, 0, 1],
  [0, 1, 0, 1, 0],
  [1, 0, 1, 0, 1],
  [0, 1, 0, 1, 0],
];

/** Captures the request the SDK actually made. */
function recorder(responseBody, status = 200) {
  const calls = [];
  const fetchMock = async (url, init) => {
    calls.push({ url: String(url), init, body: init?.body ? JSON.parse(init.body) : undefined });
    return new Response(JSON.stringify(responseBody), {
      status,
      headers: { 'content-type': 'application/json' },
    });
  };
  return { calls, fetchMock };
}

const ANALYZE_RESPONSE = {
  n: 5,
  families: [
    { family: 0, bit: 0, tie_broken: false },
    { family: 1, bit: 0, tie_broken: false },
    { family: 2, bit: 1, tie_broken: false },
    { family: 3, bit: 0, tie_broken: false },
  ],
  ones: 1,
  unanimous: false,
  tokens_used: 1,
  compute_ms: 0.55,
};

test('analyze posts the matrix itself, cell for cell', async () => {
  const { calls, fetchMock } = recorder(ANALYZE_RESPONSE);
  const client = new ZPLClient({ apiKey: KEY, fetch: fetchMock });

  await client.analyze({ matrix: CHECKERBOARD_5 });

  const analyzeCalls = calls.filter((c) => /\/analyze$/.test(c.url));
  assert.equal(analyzeCalls.length, 1, 'exactly one /analyze request expected');
  assert.deepEqual(
    analyzeCalls[0].body.matrix,
    CHECKERBOARD_5,
    'the matrix must reach the engine unchanged — this is the entire point'
  );
});

test('analyze does not reduce the matrix to a density', async () => {
  const { calls, fetchMock } = recorder(ANALYZE_RESPONSE);
  const client = new ZPLClient({ apiKey: KEY, fetch: fetchMock });

  await client.analyze({ matrix: CHECKERBOARD_5 });
  const body = calls.find((c) => /\/analyze$/.test(c.url)).body;

  assert.ok(!('bias' in body), 'a density must not be sent — it is what discards the data');
  assert.ok(!('d' in body), 'a dimension must not stand in for the matrix');
  assert.ok(!('samples' in body), 'there is nothing to sample: one matrix is one observation');
});

test('analyze returns every family, not one pooled verdict', async () => {
  const { fetchMock } = recorder(ANALYZE_RESPONSE);
  const client = new ZPLClient({ apiKey: KEY, fetch: fetchMock });

  const result = await client.analyze({ matrix: CHECKERBOARD_5 });

  assert.equal(result.families.length, 4, 'all four families must be reported');
  assert.equal(result.ones, 1);
  assert.equal(result.unanimous, false, 'a 3-1 split must not read as agreement');
  assert.equal(result.n, 5);
  for (const f of result.families) {
    assert.ok(f.bit === 0 || f.bit === 1, 'each family reports a bit');
    assert.equal(typeof f.tieBroken, 'boolean', 'tie-breaking must be visible to the caller');
  }
});

test('analyze carries no AIN and no p_output', async () => {
  const { fetchMock } = recorder(ANALYZE_RESPONSE);
  const client = new ZPLClient({ apiKey: KEY, fetch: fetchMock });

  const result = await client.analyze({ matrix: CHECKERBOARD_5 });

  // One matrix is one observation, so a proportion over it is 0 or 1 and says
  // nothing about balance. Surfacing a score here would be inventing one.
  assert.ok(!('ain' in result), 'a single matrix has no AIN');
  assert.ok(!('pOutput' in result), 'a single matrix has no output proportion');
});

test('analyze rejects malformed input before spending a request', async () => {
  const { calls, fetchMock } = recorder(ANALYZE_RESPONSE);
  const client = new ZPLClient({ apiKey: KEY, fetch: fetchMock });

  await assert.rejects(
    () => client.analyze({ matrix: [[0, 1], [1, 0]] }),
    /3x3|at least 3/i,
    'a 2x2 must be refused locally, naming the minimum'
  );
  assert.equal(
    calls.filter((c) => /\/analyze$/.test(c.url)).length,
    0,
    'no /analyze request should have been sent for invalid input'
  );
});

test('compute is untouched and still sends a density', async () => {
  // Pinned deliberately. compute() summarising the matrix is the documented,
  // shipped behaviour; this change adds a second method rather than altering
  // what existing callers receive.
  const { calls, fetchMock } = recorder({
    p_output: 0.5, ain: 0.93, ain_status: 'HIGHLY_NEUTRAL',
    deviation: 0.03, status: 'STABLE', samples: 1000, d: 5, bias: 0.48,
    tokens_used: 1, compute_ms: 1.2,
  });
  const client = new ZPLClient({ apiKey: KEY, fetch: fetchMock });

  await client.compute({ matrix: CHECKERBOARD_5, samples: 1000 });

  const computeCall = calls.find((c) => /\/compute$/.test(c.url));
  assert.ok(computeCall, 'compute must keep using /compute');
  assert.ok('bias' in computeCall.body, 'compute still sends a density, as it always has');
  assert.ok(!('matrix' in computeCall.body), 'compute has never transmitted the matrix');
});
