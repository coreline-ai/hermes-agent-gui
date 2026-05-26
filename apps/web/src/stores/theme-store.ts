import { create } from 'zustand';

export const THEMES = ['hermes', 'nous', 'bronze', 'slate', 'mono', 'glass'] as const;
export type Theme = (typeof THEMES)[number];

const STORAGE_KEY = 'hermes-gui-theme';

function initial(): Theme {
  if (typeof window === 'undefined') return 'hermes';
  const saved = window.localStorage.getItem(STORAGE_KEY) as Theme | null;
  if (saved && (THEMES as readonly string[]).includes(saved)) return saved;
  return 'hermes';
}

function applyToDom(theme: Theme): void {
  if (typeof document === 'undefined') return;
  document.documentElement.setAttribute('data-theme', theme);
}

interface ThemeState {
  theme: Theme;
  setTheme: (t: Theme) => void;
}

export const useThemeStore = create<ThemeState>((set) => {
  const start = initial();
  if (typeof window !== 'undefined') applyToDom(start);
  return {
    theme: start,
    setTheme: (t) => {
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(STORAGE_KEY, t);
        applyToDom(t);
      }
      set({ theme: t });
    },
  };
});
