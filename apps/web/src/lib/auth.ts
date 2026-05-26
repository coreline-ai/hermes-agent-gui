import { apiFetch, ApiError } from './api';

export interface User {
  name: string;
}

export interface MeResponse {
  user: User;
  expires_at: number;
}

export interface LoginResponse {
  user: User;
  expires_at: number;
}

export async function login(password: string): Promise<LoginResponse> {
  return apiFetch<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ password }),
  });
}

export async function logout(): Promise<void> {
  await apiFetch<{ ok: true }>('/api/auth/logout', { method: 'POST' });
}

export async function me(): Promise<MeResponse | null> {
  try {
    return await apiFetch<MeResponse>('/api/auth/me');
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return null;
    throw err;
  }
}
