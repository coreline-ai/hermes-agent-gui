import { createFileRoute, Link } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { Sessions, type SessionSummary } from '@/lib/api';

export const Route = createFileRoute('/sessions')({
  beforeLoad: requireAuth,
  component: SessionsPage,
});

function SessionsPage() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ['sessions'], queryFn: Sessions.list });
  const [title, setTitle] = useState('');
  const [error, setError] = useState<string | null>(null);

  const createMut = useMutation({
    mutationFn: () => Sessions.create(title || 'New chat'),
    onSuccess: () => {
      setTitle('');
      void qc.invalidateQueries({ queryKey: ['sessions'] });
    },
    onError: (e) => setError((e as Error).message),
  });

  const removeMut = useMutation({
    mutationFn: (sid: string) => Sessions.remove(sid),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  });

  const sessions = list.data?.sessions ?? [];
  const grouped = sessions.reduce<Record<string, SessionSummary[]>>((acc, session) => {
    const source = session.profile.includes(':') ? (session.profile.split(':')[0] ?? 'Web') : 'Web';
    acc[source] = [...(acc[source] ?? []), session];
    return acc;
  }, {});

  return (
    <Page
      title="Sessions"
      action={
        <Link to="/chat" className="text-xs text-sky-600 dark:text-sky-400 hover:underline">
          Open chat →
        </Link>
      }
    >
      <Card>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
        >
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Session title…"
            className="flex-1 rounded-md border border-black/10 dark:border-white/15 bg-transparent px-3 py-1.5 text-sm outline-none"
          />
          <button
            type="submit"
            disabled={createMut.isPending}
            className="rounded-md bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white text-sm px-3 py-1.5"
          >
            New
          </button>
        </form>
        <ErrorMsg>{error}</ErrorMsg>
      </Card>

      <Card>
        {list.isPending && <p className="text-xs">Loading…</p>}
        {sessions.length === 0 && !list.isPending && (
          <p className="text-xs text-black/60 dark:text-white/60">No sessions yet.</p>
        )}
        <div className="-m-4 divide-y divide-black/5 dark:divide-white/10">
          {Object.entries(grouped).map(([source, items]) => (
            <details key={source} open className="group">
              <summary className="cursor-pointer px-4 py-2 text-xs font-semibold uppercase tracking-wide text-black/55 dark:text-white/55">
                {source} · {items.length}
              </summary>
              <ul className="divide-y divide-black/5 dark:divide-white/10">
                {items.map((s: SessionSummary) => (
                  <li key={s.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{s.title}</p>
                      <p className="text-[10px] text-black/55 dark:text-white/55">
                        {s.message_count} msgs · updated {new Date(s.updated_at * 1000).toLocaleString()}
                      </p>
                    </div>
                    <button onClick={() => removeMut.mutate(s.id)} className="text-xs text-rose-600 hover:underline dark:text-rose-400">delete</button>
                  </li>
                ))}
              </ul>
            </details>
          ))}
        </div>
      </Card>
    </Page>
  );
}
