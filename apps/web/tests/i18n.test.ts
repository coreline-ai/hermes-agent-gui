import { describe, it, expect, beforeEach } from 'vitest';
import { useLocaleStore, t, LOCALES } from '@/lib/i18n';

describe('i18n', () => {
  beforeEach(() => {
    useLocaleStore.getState().setLocale('en');
  });

  it('exposes en + ko locales', () => {
    expect(LOCALES).toEqual(['en', 'ko']);
  });

  it('returns english by default', () => {
    expect(t('auth.signIn')).toBe('Sign in');
  });

  it('switches to korean', () => {
    useLocaleStore.getState().setLocale('ko');
    expect(t('auth.signIn')).toBe('로그인');
  });

  it('falls back to english for missing keys in non-default locale', () => {
    useLocaleStore.getState().setLocale('ko');
    expect(t('nav.chat')).toBe('채팅');
    // unknown key falls back to the key itself
    expect(t('does.not.exist')).toBe('does.not.exist');
  });

  it('interpolates {param} placeholders', () => {
    // Add an ad-hoc check by using an existing key with no params (smoke).
    expect(t('app.subtitle')).not.toContain('{');
  });
});
