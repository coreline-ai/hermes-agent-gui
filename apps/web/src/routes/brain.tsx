import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { Brain } from '@/lib/api';

export const Route = createFileRoute('/brain')({
  beforeLoad: requireAuth,
  component: BrainPage,
});

function BrainPage() {
  const [text, setText] = useState('Alice works at Acme Labs. Alice founded Vector Corp. Decision: use graph citations.');
  const [query, setQuery] = useState('Alice');
  const [error, setError] = useState<string | null>(null);
  const graph = useQuery({ queryKey: ['brain-graph'], queryFn: Brain.graph });
  const ask = useMutation({
    mutationFn: () => Brain.query(query),
    onError: (err) => setError(err instanceof Error ? err.message : 'query failed'),
  });
  const ingest = useMutation({
    mutationFn: () => Brain.ingest(text),
    onSuccess: () => {
      setError(null);
      void graph.refetch();
    },
    onError: (err) => setError(err instanceof Error ? err.message : 'ingest failed'),
  });

  return (
    <Page title="GBrain" action={<span className="text-xs text-black/55 dark:text-white/55">LLM-less extraction · cited synthesis</span>}>
      <div className="grid gap-4 lg:grid-cols-[420px_1fr]">
        <Card className="space-y-3">
          <textarea value={text} onChange={(e) => setText(e.target.value)} className="h-40 w-full rounded-md border border-black/10 bg-transparent p-3 text-sm dark:border-white/15" />
          <button onClick={() => ingest.mutate()} className="rounded-md bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50" disabled={ingest.isPending}>Ingest note</button>
          <div className="flex gap-2">
            <input value={query} onChange={(e) => setQuery(e.target.value)} className="flex-1 rounded-md border border-black/10 bg-transparent px-3 py-2 text-sm dark:border-white/15" />
            <button onClick={() => ask.mutate()} className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-50" disabled={ask.isPending}>Ask</button>
          </div>
          <ErrorMsg>{error}</ErrorMsg>
          {ask.data && <Answer data={ask.data.synthesis} />}
        </Card>
        <Card>
          <div className="mb-3 flex items-center justify-between text-sm">
            <strong>Local graph</strong>
            <span className="text-xs text-black/50 dark:text-white/50">{graph.data?.nodes.length ?? 0} nodes · {graph.data?.edges.length ?? 0} edges</span>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-black/55 dark:text-white/55">Nodes</h3>
              <ul className="mt-2 space-y-1 text-sm">
                {(graph.data?.nodes ?? []).slice(0, 30).map((node) => <li key={node.id} className="rounded bg-black/[0.03] px-2 py-1 dark:bg-white/[0.04]">{node.label} <span className="text-[10px] text-black/45">{node.kind}</span></li>)}
              </ul>
            </section>
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-black/55 dark:text-white/55">Edges</h3>
              <ul className="mt-2 space-y-1 text-xs">
                {(graph.data?.edges ?? []).slice(0, 30).map((edge) => <li key={edge.id} className="rounded bg-black/[0.03] px-2 py-1 font-mono dark:bg-white/[0.04]">{edge.src.slice(0, 6)} → {edge.dst.slice(0, 6)} · {edge.kind}</li>)}
              </ul>
            </section>
          </div>
        </Card>
      </div>
    </Page>
  );
}

function Answer({ data }: { data: { answer: string; citations: { node_id: string; label: string; edge: string }[]; gap_analysis: string[] } }) {
  return (
    <div className="rounded-lg border border-black/5 p-3 text-sm dark:border-white/10">
      <p>{data.answer}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {data.citations.map((citation) => <span key={`${citation.node_id}-${citation.edge}`} className="rounded-full bg-emerald-500/10 px-2 py-1 text-[11px] text-emerald-700 dark:text-emerald-300">{citation.label} · {citation.edge}</span>)}
        {data.gap_analysis.map((gap) => <span key={gap} className="rounded-full bg-amber-500/10 px-2 py-1 text-[11px] text-amber-700 dark:text-amber-300">{gap}</span>)}
      </div>
    </div>
  );
}
