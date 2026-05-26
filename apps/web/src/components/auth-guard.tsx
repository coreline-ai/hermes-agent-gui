import { redirect } from '@tanstack/react-router';
import { useAuthStore } from '@/stores/auth-store';

/** Use in TanStack Router ``beforeLoad`` to gate authenticated routes. */
export async function requireAuth(): Promise<void> {
  const store = useAuthStore.getState();
  if (store.status === 'unknown') await store.hydrate();
  if (useAuthStore.getState().status !== 'authenticated') {
    throw redirect({ to: '/login' });
  }
}
