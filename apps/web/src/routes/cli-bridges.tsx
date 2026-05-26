import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { CliBridges } from '@/lib/api';

export const Route = createFileRoute('/cli-bridges')({ beforeLoad: requireAuth, component: CliBridgesPage });

function CliBridgesPage() {
  const bridges = useQuery({ queryKey: ['cli-bridges'], queryFn: CliBridges.list });
  const [selected, setSelected] = useState('codex');
  const [prompt, setPrompt] = useState('hello');
  const [error, setError] = useState<string | null>(null);
  const run = useMutation({
    mutationFn: () => CliBridges.run(selected, prompt),
    onError: (err) => setError(err instanceof Error ? err.message : 'bridge failed'),
    onSuccess: () => setError(null),
  });
  return (
    <Page title="Multi-CLI Bridge" action={<span className="text-xs text-black/55 dark:text-white/55">Claude Code · Codex · Gemini · OpenCode · OpenClaw</span>}>
      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <Card className="space-y-2">
          {(bridges.data?.bridges ?? []).map((bridge) => (
            <button key={bridge.name} onClick={() => setSelected(bridge.name)} className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm ${selected === bridge.name ? 'bg-sky-500/15 text-sky-700 dark:text-sky-300' : 'hover:bg-black/5 dark:hover:bg-white/10'}`}>
              <span>{bridge.name}</span>
              <span className={`text-[10px] ${bridge.available ? 'text-emerald-600' : 'text-black/40 dark:text-white/40'}`}>{bridge.available ? 'available' : 'install'}</span>
            </button>
          ))}
        </Card>
        <Card className="space-y-3">
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} className="h-32 w-full rounded-md border border-black/10 bg-transparent p-3 text-sm dark:border-white/15" />
          <button onClick={() => run.mutate()} disabled={run.isPending} className="rounded-md bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50">Run selected CLI</button>
          <ErrorMsg>{error}</ErrorMsg>
          {run.data?.output && <pre className="whitespace-pre-wrap rounded bg-black/[0.03] p-3 text-xs dark:bg-white/[0.04]">{run.data.output}</pre>}
        </Card>
      </div>
    </Page>
  );
}
