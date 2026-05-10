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
    return new Response(
      JSON.stringify({
        status: 'healthy',
        version: 'test',
      }),
      { status: 200, headers: { 'content-type': 'application/json' } }
    );
  };

  const client = new ZPLClient({
    apiKey: 'zpl_u_placeholder_not_a_real_key',
    fetch: fetchMock,
  });
  await client.getHealth();

  assert.equal(headerGet(seen, 'X-ZPL-Client'), ZPL_SDK_CLIENT_TYPE);
  assert.equal(headerGet(seen, 'X-ZPL-Client-Version'), SDK_VERSION);
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
    apiKey: 'zpl_u_placeholder_not_a_real_key',
    fetch: fetchMock,
    xZplClient: 'custom-bridge',
    xZplClientVersion: '9.8.7',
  });
  await client.getPlans();

  assert.equal(headerGet(seen, 'X-ZPL-Client'), 'custom-bridge');
  assert.equal(headerGet(seen, 'X-ZPL-Client-Version'), '9.8.7');
});
