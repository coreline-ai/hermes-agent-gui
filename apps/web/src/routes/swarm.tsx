import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { Swarm, Conductor, type Mission, ApiError } from '@/lib/api';

export const Route = createFileRoute('/swarm')({
  beforeLoad: requireAuth,
  component: SwarmPage,
});

function SwarmPage() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ['swarm'], queryFn: Swarm.list, refetchInterval: 5_000 });
  const [prompt, setPrompt] = useState('');
  const [mission, setMission] = useState<Mission | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const dispatch = useMutation({
    mutationFn: () => Conductor.dispatch(prompt),
    onSuccess: (m) => {
      setMission(m);
      setErr(null);
    },
    onError: (e) =>
      setErr(e instanceof ApiError ? JSON.stringify(e.payload) : (e as Error).message),
  });

  return (
    <Page title="Swarm + Conductor" action={<span className="text-[10px] text-black/55 dark:text-white/55">tmux: {list.data?.tmux ? 'yes' : 'no (subprocess fallback)'}</span>}>
      <Card>
        <h3 className="text-sm font-medium mb-2">Conductor — dispatch a mission</h3>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (prompt.trim()) dispatch.mutate();
          }}
          className="space-y-2"
        >
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
            placeholder="build the chat UI. review the auth flow. test the cron scheduler."
            className="w-full rounded-md border border-black/10 dark:border-white/15 bg-transparent px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={dispatch.isPending || !prompt.trim()}
            className="rounded-md bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white text-sm px-3 py-1.5"
          >
            {dispatch.isPending ? 'Dispatching…' : 'Dispatch'}
          </button>
        </form>
        <ErrorMsg>{err}</ErrorMsg>
        {mission && (
          <div className="mt-3 space-y-1">
            <p className="text-xs font-mono text-black/55 dark:text-white/55">
              mission {mission.id}
            </p>
            <ol className="text-xs space-y-1">
              {mission.sub_tasks.map((t) => (
                <li key={t.order} className="flex gap-2">
                  <span className="text-[10px] uppercase tracking-wide w-20 text-black/60 dark:text-white/60">
                    {t.role}
                  </span>
                  <span>{t.text}</span>
                </li>
              ))}
            </ol>
          </div>
        )}
      </Card>

      <Card>
        <h3 className="text-sm font-medium mb-2">Workers</h3>
        {(list.data?.workers ?? []).length === 0 && (
          <p className="text-xs text-black/60 dark:text-white/60">No workers running.</p>
        )}
        <ul className="text-xs space-y-1.5">
          {(list.data?.workers ?? []).map((w) => (
            <li key={w.id} className="flex items-center justify-between border-b border-black/5 dark:border-white/10 pb-1.5">
              <div className="min-w-0">
                <p className="font-mono">{w.role} · {w.id}</p>
                <p className="text-[10px] text-black/55 dark:text-white/55 truncate">
                  {w.cmd.join(' ')} · {w.state}
                </p>
              </div>
              <button
                onClick={() => Swarm.kill(w.id).then(() => qc.invalidateQueries({ queryKey: ['swarm'] }))}
                className="text-[10px] text-rose-600 dark:text-rose-400 hover:underline"
              >
                kill
              </button>
            </li>
          ))}
        </ul>
      </Card>
    </Page>
  );
}
