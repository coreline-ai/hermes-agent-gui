import { create } from 'zustand';
import type { User } from '@/lib/auth';
import { me as fetchMe, login as apiLogin, logout as apiLogout } from '@/lib/auth';

export type AuthStatus = 'unknown' | 'authenticated' | 'unauthenticated';

interface AuthState {
  status: AuthStatus;
  user: User | null;
  expiresAt: number | null;
  hydrate: () => Promise<void>;
  login: (password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  status: 'unknown',
  user: null,
  expiresAt: null,
  hydrate: async () => {
    const result = await fetchMe();
    if (result) {
      set({ status: 'authenticated', user: result.user, expiresAt: result.expires_at });
    } else {
      set({ status: 'unauthenticated', user: null, expiresAt: null });
    }
  },
  login: async (password: string) => {
    const result = await apiLogin(password);
    set({ status: 'authenticated', user: result.user, expiresAt: result.expires_at });
  },
  logout: async () => {
    await apiLogout();
    set({ status: 'unauthenticated', user: null, expiresAt: null });
  },
}));
