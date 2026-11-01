import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient, checkHealth } from '../api';

describe('API Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('performs successful GET request and returns data', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ status: 'ok', version: '0.1.0' }),
      }),
    );

    const res = await checkHealth();
    expect(res.data).toEqual({ status: 'ok', version: '0.1.0' });
    expect(res.error).toBeNull();
    expect(res.status).toBe(200);
  });

  it('handles HTTP error responses gracefully', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Not Found' }),
      }),
    );

    const res = await apiClient.get('/nonexistent');
    expect(res.data).toBeNull();
    expect(res.error).toBe('Not Found');
    expect(res.status).toBe(404);
  });

  it('handles network failure gracefully', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new Error('Network connection failed')),
    );

    const res = await apiClient.get('/test');
    expect(res.data).toBeNull();
    expect(res.error).toBe('Network connection failed');
    expect(res.status).toBe(0);
  });

  it('sends POST requests with JSON payload', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ trip_id: '123' }),
    });
    vi.stubGlobal('fetch', mockFetch);

    const payload = { origin: 'Tokyo' };
    const res = await apiClient.post('/trips/plan', payload);

    expect(res.data).toEqual({ trip_id: '123' });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/trips/plan'),
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
    );
  });

  it('formats FastAPI validation error arrays cleanly', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        headers: { get: () => 'application/json' },
        json: async () => ({
          detail: [
            { msg: 'Trip end date must be after start date.', loc: ['body'] },
            { msg: 'Travelers must be at least 1.', loc: ['body', 'travelers'] },
          ],
        }),
      }),
    );

    const res = await apiClient.post('/trips/plan', {});
    expect(res.data).toBeNull();
    expect(res.error).toBe(
      'Trip end date must be after start date.; Travelers must be at least 1.',
    );
    expect(res.status).toBe(422);
  });

  it('calls getTrip with tripId', async () => {
    const mockTrip = { trip_id: 'trip_abc' };
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => mockTrip,
      }),
    );

    const { getTrip } = await import('../api');
    const res = await getTrip('trip_abc');
    expect(res.data).toEqual(mockTrip);
    expect(res.status).toBe(200);
  });

  it('calls checkHealthReady endpoint', async () => {
    const mockReady = { status: 'ready', rag_enabled: true };
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => mockReady,
      }),
    );

    const { checkHealthReady } = await import('../api');
    const res = await checkHealthReady();
    expect(res.data).toEqual(mockReady);
    expect(res.status).toBe(200);
  });
});
