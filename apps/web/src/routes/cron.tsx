import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { Cron, ApiError } from '@/lib/api';

export const Route = createFileRoute('/cron')({
  beforeLoad: requireAuth,
  component: CronPage,
});

function CronPage() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ['cron'], queryFn: Cron.list, refetchInterval: 15_000 });
  const [name, setName] = useState('');
  const [schedule, setSchedule] = useState('*/5 * * * *');
  const [command, setCommand] = useState('');
  const [err, setErr] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () => Cron.create({ name, schedule, command }),
    onSuccess: () => {
      setName('');
      setCommand('');
      setErr(null);
      void qc.invalidateQueries({ queryKey: ['cron'] });
    },
    onError: (e) =>
      setErr(e instanceof ApiError ? JSON.stringify(e.payload) : (e as Error).message),
  });

  return (
    <Page title="Cron jobs">
      <Card>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (name && schedule && command) create.mutate();
          }}
          className="grid grid-cols-1 sm:grid-cols-[150px_140px_1fr_auto] gap-2"
        >
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="name" className="rounded-md border border-black/10 dark:border-white/15 bg-transparent px-2 py-1.5 text-sm" />
          <input value={schedule} onChange={(e) => setSchedule(e.target.value)} placeholder="m h dom mon dow" className="rounded-md border border-black/10 dark:border-white/15 bg-transparent px-2 py-1.5 text-xs font-mono" />
          <input value={command} onChange={(e) => setCommand(e.target.value)} placeholder="shell command" className="rounded-md border border-black/10 dark:border-white/15 bg-transparent px-2 py-1.5 text-sm font-mono" />
          <button type="submit" disabled={create.isPending} className="rounded-md bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white text-sm px-3 py-1.5">Add</button>
        </form>
        <ErrorMsg>{err}</ErrorMsg>
      </Card>

      <div className="space-y-2">
        {(list.data?.jobs ?? []).map((j) => (
          <Card key={j.id}>
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{j.name}</p>
                <p className="text-[11px] font-mono text-black/60 dark:text-white/60">
                  {j.schedule} · <code>{j.command}</code>
                </p>
              </div>
              <div className="flex gap-1">
                <button
                  onClick={() => Cron.runNow(j.id).then(() => qc.invalidateQueries({ queryKey: ['cron'] }))}
                  className="text-xs rounded-md border border-black/10 dark:border-white/15 px-2 py-1"
                >
                  run now
                </button>
                <button
                  onClick={() => Cron.remove(j.id).then(() => qc.invalidateQueries({ queryKey: ['cron'] }))}
                  className="text-xs text-rose-600 dark:text-rose-400 px-2 py-1"
                >
                  del
                </button>
              </div>
            </div>
            {j.last_run_at && (
              <p className="mt-2 text-[10px] font-mono text-black/55 dark:text-white/55">
                last run {new Date(j.last_run_at * 1000).toLocaleString()} · exit {j.last_exit_code}
              </p>
            )}
            {j.last_output && (
              <pre className="mt-1 text-[10px] whitespace-pre-wrap break-all bg-black/[0.02] dark:bg-white/[0.03] rounded p-2 max-h-32 overflow-auto">
                {j.last_output}
              </pre>
            )}
          </Card>
        ))}
        {list.data && list.data.jobs.length === 0 && (
          <p className="text-xs text-black/60 dark:text-white/60">No cron jobs.</p>
        )}
      </div>
    </Page>
  );
}
