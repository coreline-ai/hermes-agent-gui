import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { Rag } from '@/lib/api';

export const Route = createFileRoute('/rag')({
  beforeLoad: requireAuth,
  component: RagPage,
});

function RagPage() {
  const [sessionId, setSessionId] = useState('');
  const [query, setQuery] = useState('');
  const [error, setError] = useState<string | null>(null);

  const memory = useQuery({
    queryKey: ['rag-memory', sessionId],
    queryFn: () => Rag.sessionMemory(sessionId.trim()),
    enabled: Boolean(sessionId.trim()),
  });

  const compact = useMutation({
    mutationFn: () => Rag.compact(sessionId.trim()),
    onSuccess: () => {
      setError(null);
      void memory.refetch();
    },
    onError: (err) => setError(err instanceof Error ? err.message : 'compact failed'),
  });

  const search = useQuery({
    queryKey: ['rag-search', query, sessionId],
    queryFn: () => Rag.search(query.trim(), 5, sessionId.trim() || undefined),
    enabled: Boolean(query.trim()),
  });

  return (
    <Page title="Auto-Compress + RAG" action={<span className="text-xs text-black/55 dark:text-white/55">Visible transcript stays unchanged</span>}>
      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <Card className="space-y-3">
          <div>
            <label className="text-[11px] font-medium uppercase tracking-wide text-black/55 dark:text-white/55">Session ID</label>
            <input
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              placeholder="Paste a session id"
              className="mt-1 w-full rounded-md border border-black/10 bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-sky-500/40 dark:border-white/15"
            />
          </div>
          <button
            onClick={() => compact.mutate()}
            disabled={!sessionId.trim() || compact.isPending}
            className="rounded-md bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50"
          >
            {compact.isPending ? 'Compacting…' : 'Compact now'}
          </button>
          <p className="text-xs leading-relaxed text-black/60 dark:text-white/60">
            Phase 18 stores compact summaries in a hidden memory index, then injects only relevant chunks into Hermes Agent requests.
          </p>
          <ErrorMsg>{error}</ErrorMsg>
        </Card>

        <Card className="space-y-3">
          <div>
            <label className="text-[11px] font-medium uppercase tracking-wide text-black/55 dark:text-white/55">Search compressed memory</label>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="redis decision, architecture note…"
              className="mt-1 w-full rounded-md border border-black/10 bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-sky-500/40 dark:border-white/15"
            />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <ChunkList title="Session chunks" chunks={memory.data?.chunks ?? []} loading={memory.isPending && Boolean(sessionId)} />
            <ChunkList title="Search results" chunks={search.data?.results ?? []} loading={search.isFetching} />
          </div>
        </Card>
      </div>
    </Page>
  );
}

function ChunkList({ title, chunks, loading }: { title: string; chunks: Awaited<ReturnType<typeof Rag.search>>['results']; loading: boolean }) {
  return (
    <section className="rounded-lg border border-black/5 p-3 dark:border-white/10">
      <h3 className="text-sm font-semibold">{title}</h3>
      {loading && <p className="mt-2 text-xs text-black/55 dark:text-white/55">Loading…</p>}
      {!loading && chunks.length === 0 && <p className="mt-2 text-xs text-black/55 dark:text-white/55">No chunks yet.</p>}
      <ul className="mt-2 space-y-2">
        {chunks.map((chunk) => (
          <li key={chunk.id} className="rounded-md bg-black/[0.03] p-2 text-xs leading-relaxed dark:bg-white/[0.04]">
            <div className="mb-1 flex items-center justify-between gap-2 font-mono text-[10px] text-black/50 dark:text-white/50">
              <span>{chunk.range_start}–{chunk.range_end}</span>
              {typeof chunk.score === 'number' && <span>{chunk.score.toFixed(2)}</span>}
            </div>
            <p className="line-clamp-5 whitespace-pre-wrap">{chunk.summary}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
