import { describe, expect, it } from 'vitest';

import { buildHeaders, fetchHealth, REQUEST_ID_HEADER } from './client';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

describe('buildHeaders', () => {
  it('always sends a correlation ID and accepts JSON', () => {
    const headers = buildHeaders(undefined, 'req-ui-1');

    expect(headers[REQUEST_ID_HEADER]).toBe('req-ui-1');
    expect(headers.Accept).toBe('application/json');
    expect(headers.Authorization).toBeUndefined();
  });

  it('adds a bearer token when one is given', () => {
    expect(buildHeaders('stub-token-alice', 'req-ui-2').Authorization).toBe('Bearer stub-token-alice');
  });

  it('generates a UUID correlation ID by default', () => {
    expect(buildHeaders()[REQUEST_ID_HEADER]).toMatch(/^[0-9a-f-]{36}$/);
  });
});

describe('fetchHealth', () => {
  it('returns the healthy body on 200', async () => {
    const health = await fetchHealth(async () => jsonResponse(200, { status: 'ok', db: 'connected' }));

    expect(health).toEqual({ status: 'ok', db: 'connected' });
  });

  it('returns the unavailable body on 503 instead of throwing', async () => {
    const health = await fetchHealth(async () => jsonResponse(503, { status: 'unavailable', db: 'unreachable' }));

    expect(health.status).toBe('unavailable');
  });

  it('throws on any other status', async () => {
    await expect(fetchHealth(async () => jsonResponse(500, {}))).rejects.toThrow('Unexpected health status 500');
  });
});
