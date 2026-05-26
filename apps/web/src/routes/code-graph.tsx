import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { CodeGraph } from '@/lib/api';

export const Route = createFileRoute('/code-graph')({
  beforeLoad: requireAuth,
  component: CodeGraphPage,
});

function CodeGraphPage() {
  const [root, setRoot] = useState('.');
  const [query, setQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  const symbols = useQuery({ queryKey: ['code-symbols', query], queryFn: () => CodeGraph.symbols(query), enabled: true });
  const index = useMutation({
    mutationFn: () => CodeGraph.index(root),
    onSuccess: () => {
      setError(null);
      void symbols.refetch();
    },
    onError: (err) => setError(err instanceof Error ? err.message : 'index failed'),
  });

  return (
    <Page title="Code Graph" action={<span className="text-xs text-black/55 dark:text-white/55">Python · TS · JS · Go · Rust symbols</span>}>
      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <Card className="space-y-3">
          <label className="block text-xs font-medium text-black/60 dark:text-white/60">Workspace root</label>
          <input value={root} onChange={(e) => setRoot(e.target.value)} className="w-full rounded-md border border-black/10 bg-transparent px-3 py-2 text-sm dark:border-white/15" />
          <button onClick={() => index.mutate()} disabled={index.isPending} className="rounded-md bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50">{index.isPending ? 'Indexing…' : 'Index workspace'}</button>
          {index.data && <p className="text-xs text-black/60 dark:text-white/60">{index.data.files} files · {index.data.symbols} symbols · {index.data.elapsed_ms}ms</p>}
          <ErrorMsg>{error}</ErrorMsg>
        </Card>
        <Card>
          <div className="mb-3 flex items-center gap-2">
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="find_definition symbol…" className="flex-1 rounded-md border border-black/10 bg-transparent px-3 py-2 text-sm dark:border-white/15" />
          </div>
          <ul className="divide-y divide-black/5 text-sm dark:divide-white/10">
            {(symbols.data?.symbols ?? []).map((symbol) => (
              <li key={`${symbol.file}:${symbol.line}:${symbol.name}`} className="grid gap-2 py-2 md:grid-cols-[160px_1fr_70px]">
                <span className="font-medium">{symbol.name}</span>
                <span className="truncate font-mono text-xs text-black/55 dark:text-white/55">{symbol.file}</span>
                <span className="text-right font-mono text-xs">{symbol.kind}:{symbol.line}</span>
              </li>
            ))}
            {symbols.data?.symbols.length === 0 && <li className="py-8 text-center text-xs text-black/55 dark:text-white/55">No symbols indexed yet.</li>}
          </ul>
        </Card>
      </div>
    </Page>
  );
}
