import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('auth store', () => {
  beforeEach(() => vi.resetModules());

  it('hydrates to authenticated when /api/auth/me returns 200', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url === '/api/auth/me') {
          return new Response(
            JSON.stringify({ user: { name: 'local' }, expires_at: 9999999 }),
            { status: 200, headers: { 'content-type': 'application/json' } },
          );
        }
        throw new Error(`unexpected url ${url}`);
      }),
    );
    const { useAuthStore } = await import('@/stores/auth-store');
    await useAuthStore.getState().hydrate();
    expect(useAuthStore.getState().status).toBe('authenticated');
    expect(useAuthStore.getState().user?.name).toBe('local');
    vi.unstubAllGlobals();
  });

  it('hydrates to unauthenticated on 401', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response('{"error":"not_authenticated"}', {
          status: 401,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    );
    const { useAuthStore } = await import('@/stores/auth-store');
    await useAuthStore.getState().hydrate();
    expect(useAuthStore.getState().status).toBe('unauthenticated');
    expect(useAuthStore.getState().user).toBeNull();
    vi.unstubAllGlobals();
  });
});
