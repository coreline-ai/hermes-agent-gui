import { createFileRoute, redirect } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { getHealth } from '@/lib/api';
import { useAuthStore } from '@/stores/auth-store';

export const Route = createFileRoute('/')({
  beforeLoad: async () => {
    const store = useAuthStore.getState();
    if (store.status === 'unknown') {
      await store.hydrate();
    }
    const now = useAuthStore.getState();
    if (now.status === 'authenticated') {
      throw redirect({ to: '/chat' });
    }
    throw redirect({ to: '/login' });
  },
  component: IndexFallback,
});

// Unreachable in practice — beforeLoad always redirects. Kept as a safety net so
// the route module never renders nothing during loader transitions.
function IndexFallback() {
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth, retry: 1 });
  return (
    <section className="max-w-xl mx-auto space-y-3">
      <p className="text-sm text-black/70 dark:text-white/70">Loading…</p>
      <pre className="text-[11px] rounded-md border border-black/5 dark:border-white/10 p-3 bg-black/[0.02] dark:bg-white/[0.03]">
        {JSON.stringify(health.data ?? health.error ?? null, null, 2)}
      </pre>
    </section>
  );
}
