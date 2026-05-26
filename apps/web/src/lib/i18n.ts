/**
 * Phase 13 — i18n (en + ko per locked decision #6).
 *
 * Tiny runtime: no react-intl, no i18next. Adapted from A's lib/i18n.ts —
 * just a key → string lookup plus a ``t()`` helper with parameter interp.
 */
import en from '@/locales/en.json';
import ko from '@/locales/ko.json';
import { create } from 'zustand';

export const LOCALES = ['en', 'ko'] as const;
export type Locale = (typeof LOCALES)[number];

const CATALOGS: Record<Locale, Record<string, string>> = { en, ko };
const STORAGE_KEY = 'hermes-gui-locale';

function pickInitialLocale(): Locale {
  if (typeof window === 'undefined') return 'en';
  const saved = window.localStorage.getItem(STORAGE_KEY) as Locale | null;
  if (saved && (LOCALES as readonly string[]).includes(saved)) return saved;
  const nav = window.navigator.language?.slice(0, 2);
  return (nav === 'ko' ? 'ko' : 'en') as Locale;
}

interface LocaleState {
  locale: Locale;
  setLocale: (l: Locale) => void;
}

export const useLocaleStore = create<LocaleState>((set) => ({
  locale: pickInitialLocale(),
  setLocale: (l) => {
    if (typeof window !== 'undefined') window.localStorage.setItem(STORAGE_KEY, l);
    set({ locale: l });
  },
}));

/** Translate. Falls back to English if a key is missing in the active locale,
 *  then to the key itself. ``{name}`` style placeholders are interpolated. */
export function t(key: string, params?: Record<string, string | number>): string {
  const { locale } = useLocaleStore.getState();
  const catalog = CATALOGS[locale] ?? CATALOGS.en;
  let value = catalog[key] ?? CATALOGS.en[key] ?? key;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      value = value.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
    }
  }
  return value;
}

/** React hook variant — re-renders when the active locale changes. */
export function useT(): (key: string, params?: Record<string, string | number>) => string {
  // Subscribing to the store ensures components re-render on locale change.
  useLocaleStore((s) => s.locale);
  return t;
}
