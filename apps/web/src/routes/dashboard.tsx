import { createFileRoute, Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card } from '@/components/page';
import { Dashboard } from '@/lib/api';

export const Route = createFileRoute('/dashboard')({
  beforeLoad: requireAuth,
  component: DashboardPage,
});

function DashboardPage() {
  const data = useQuery({ queryKey: ['dashboard'], queryFn: Dashboard.get, refetchInterval: 10_000 });
  const logs = useQuery({ queryKey: ['logs'], queryFn: () => Dashboard.logs(50) });

  return (
    <Page title="Dashboard">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Sessions" value={data.data?.summary.sessions} />
        <Stat label="Tasks" value={data.data?.summary.tasks} />
        <Stat label="Cron jobs" value={data.data?.summary.cron_jobs} />
        <Stat
          label="Agent"
          value={data.data?.agent.configured ? (data.data.agent.reachable ? 'ok' : 'down') : 'off'}
        />
      </div>

      <Card>
        <h3 className="text-sm font-medium mb-2">Recent sessions</h3>
        {data.data?.summary.recent_sessions.length === 0 && (
          <p className="text-xs text-black/60 dark:text-white/60">None.</p>
        )}
        <ul className="space-y-1 text-xs">
          {(data.data?.summary.recent_sessions ?? []).map((s) => (
            <li key={s.id} className="flex items-center justify-between">
              <Link to="/sessions" className="hover:underline">
                {s.title}
              </Link>
              <span className="text-[10px] text-black/55 dark:text-white/55">
                {new Date(s.updated_at * 1000).toLocaleString()}
              </span>
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <h3 className="text-sm font-medium mb-2">Inspector logs (redacted)</h3>
        {logs.isPending && <p className="text-xs">Loading…</p>}
        <pre className="text-[10px] whitespace-pre-wrap break-all max-h-64 overflow-auto">
          {(logs.data?.lines ?? []).join('\n') || '(no logs yet)'}
        </pre>
      </Card>
    </Page>
  );
}

function Stat({ label, value }: { label: string; value: number | string | undefined }) {
  return (
    <Card>
      <p className="text-[10px] uppercase tracking-wide text-black/55 dark:text-white/55">{label}</p>
      <p className="text-xl font-semibold mt-1">{value ?? '—'}</p>
    </Card>
  );
}
