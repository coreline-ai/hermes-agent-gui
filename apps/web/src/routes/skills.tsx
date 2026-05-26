import { createFileRoute } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card } from '@/components/page';
import { Skills } from '@/lib/api';

export const Route = createFileRoute('/skills')({
  beforeLoad: requireAuth,
  component: SkillsPage,
});

function SkillsPage() {
  const q = useQuery({ queryKey: ['skills'], queryFn: Skills.list });
  const skills = q.data?.skills ?? [];

  return (
    <Page title="Skills" action={<span className="text-[10px] text-black/50 dark:text-white/50">source: {q.data?.source ?? '…'}</span>}>
      {q.isPending && <p className="text-xs">Loading…</p>}
      {!q.isPending && skills.length === 0 && (
        <Card>
          <p className="text-xs text-black/60 dark:text-white/60">
            No skills installed. The local browser scans <code>~/.hermes/skills</code> and the
            gateway path is used when <code>HERMES_API_URL</code> is configured.
          </p>
        </Card>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {skills.map((s) => (
          <Card key={s.id}>
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium">{s.name}</h3>
              <span className="text-[10px] uppercase tracking-wide text-black/55 dark:text-white/55">
                {s.origin}
              </span>
            </div>
            {s.description && (
              <p className="mt-1 text-xs text-black/70 dark:text-white/70 whitespace-pre-wrap">
                {s.description}
              </p>
            )}
            {s.path && <p className="mt-1 text-[10px] font-mono text-black/50 dark:text-white/50">{s.path}</p>}
          </Card>
        ))}
      </div>
    </Page>
  );
}
