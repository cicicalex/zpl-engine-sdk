import test from 'node:test';
import assert from 'node:assert/strict';
import { ZPLClient, SDK_VERSION, ZPL_SDK_CLIENT_TYPE } from '../dist/index.js';

function headerGet(headers, name) {
  if (!headers) return undefined;
  if (typeof headers.get === 'function') return headers.get(name);
  const key = Object.keys(headers).find((k) => k.toLowerCase() === name.toLowerCase());
  return key ? headers[key] : undefined;
}

test('ZPLClient sends ADR 0002 headers by default', async () => {
  let seen;
  const fetchMock = async (_url, init) => {
    seen = init.headers;
    // The engine's actual /health body. It used to read `status: 'healthy'`,
    // a value no engine has ever sent — mocks that echo the SDK's wishes
    // rather than the wire are how the HealthResponse type stayed wrong.
    return new Response(
      JSON.stringify({
        status: 'ok',
        version: 'test',
        uptime_seconds: 42,
      }),
      { status: 200, headers: { 'content-type': 'application/json' } }
    );
  };

  const client = new ZPLClient({
    apiKey: 'zpl_u_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6',
    fetch: fetchMock,
  });
  await client.getHealth();

  assert.equal(headerGet(seen, 'X-ZPL-Client'), ZPL_SDK_CLIENT_TYPE);
  assert.equal(headerGet(seen, 'X-ZPL-Client-Version'), SDK_VERSION);
});

test('SDK_VERSION is the version this package actually ships as', async () => {
  // AUDIT 2026-07-31: the assertion above compares the header to SDK_VERSION,
  // and the header is built from SDK_VERSION. It compares the constant to
  // itself and passes for any value - which is how the package reached 2.1.0
  // in package.json while this constant still said 2.0.6. Every
  // X-ZPL-Client-Version header from a 2.1.0 install would have reported
  // 2.0.6, permanently: a published tarball cannot be edited.
  //
  // What that costs, beyond tidiness: admin funnel dashboards read 2.1.0
  // adoption as zero, and setting the engine's ZPL_MIN_VERSION_SDK_TYPESCRIPT
  // floor to 2.1.0 later would 426 every up-to-date install.
  //
  // The only assertion that can catch it is one against a source the constant
  // is not derived from.
  const { readFile } = await import('node:fs/promises');
  const { fileURLToPath } = await import('node:url');
  const { dirname, join } = await import('node:path');

  const root = dirname(dirname(fileURLToPath(import.meta.url)));
  const pkg = JSON.parse(await readFile(join(root, 'package.json'), 'utf-8'));

  assert.equal(
    SDK_VERSION,
    pkg.version,
    `SDK_VERSION is '${SDK_VERSION}' but this package publishes as '${pkg.version}'. ` +
      `Every client-version header, heartbeat and version gate would report the wrong ` +
      `number, and npm does not let you edit a published tarball.`,
  );
});

test('ZPLClient allows overriding ADR 0002 headers', async () => {
  let seen;
  const fetchMock = async (_url, init) => {
    seen = init.headers;
    return new Response(JSON.stringify({ plans: [] }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    });
  };

  const client = new ZPLClient({
    apiKey: 'zpl_u_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6',
    fetch: fetchMock,
    xZplClient: 'custom-bridge',
    xZplClientVersion: '9.8.7',
  });
  await client.getPlans();

  assert.equal(headerGet(seen, 'X-ZPL-Client'), 'custom-bridge');
  assert.equal(headerGet(seen, 'X-ZPL-Client-Version'), '9.8.7');
});
