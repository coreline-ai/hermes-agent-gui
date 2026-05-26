import { createFileRoute, useNavigate, redirect } from '@tanstack/react-router';
import { type FormEvent, useState } from 'react';
import { useAuthStore } from '@/stores/auth-store';
import { ApiError } from '@/lib/api';

export const Route = createFileRoute('/login')({
  beforeLoad: async () => {
    const store = useAuthStore.getState();
    if (store.status === 'unknown') {
      await store.hydrate();
    }
    if (useAuthStore.getState().status === 'authenticated') {
      throw redirect({ to: '/chat' });
    }
  },
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const [password, setPassword] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      await login(password);
      void navigate({ to: '/chat' });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 501) setError('Password login is not enabled on this server.');
        else if (err.status === 401) setError('Incorrect password.');
        else if (err.status === 429) setError('Too many attempts — slow down for a minute.');
        else setError(`Login failed (${err.status}).`);
      } else {
        setError('Network error — is the backend running?');
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="max-w-sm mx-auto space-y-4 mt-8">
      <header className="space-y-1">
        <h2 className="text-xl font-semibold">Sign in</h2>
        <p className="text-xs text-black/60 dark:text-white/60">
          Phase 1 · password auth. Configure via <code>HERMES_GUI_PASSWORD</code>.
        </p>
      </header>
      <form onSubmit={onSubmit} className="space-y-3">
        <label className="block">
          <span className="text-xs font-medium">Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
            required
            disabled={pending}
            className="mt-1 w-full rounded-md border border-black/10 dark:border-white/15 bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-sky-500/40"
          />
        </label>
        {error && (
          <p className="text-xs text-rose-600 dark:text-rose-400" role="alert">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={pending || password.length === 0}
          className="w-full rounded-md bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white text-sm font-medium py-2"
        >
          {pending ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </section>
  );
}
