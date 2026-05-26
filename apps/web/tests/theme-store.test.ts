import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('theme store', () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
    vi.resetModules();
  });

  it('defaults to hermes on first load', async () => {
    const mod = await import('@/stores/theme-store');
    expect(mod.useThemeStore.getState().theme).toBe('hermes');
  });

  it('persists across reads via localStorage', async () => {
    const { useThemeStore } = await import('@/stores/theme-store');
    useThemeStore.getState().setTheme('glass');
    expect(window.localStorage.getItem('hermes-gui-theme')).toBe('glass');
    expect(document.documentElement.getAttribute('data-theme')).toBe('glass');
  });

  it('applies data-theme attribute', async () => {
    const { useThemeStore } = await import('@/stores/theme-store');
    useThemeStore.getState().setTheme('slate');
    expect(document.documentElement.getAttribute('data-theme')).toBe('slate');
  });
});
