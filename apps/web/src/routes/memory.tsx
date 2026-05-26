import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { Memory, ApiError } from '@/lib/api';

export const Route = createFileRoute('/memory')({
  beforeLoad: requireAuth,
  component: MemoryPage,
});

function MemoryPage() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ['memory'], queryFn: Memory.list });
  const [selected, setSelected] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [err, setErr] = useState<string | null>(null);

  const read = useQuery({
    queryKey: ['memory', 'read', selected],
    queryFn: () => Memory.read(selected as string),
    enabled: !!selected,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (read.data) setDraft(read.data.content);
  }, [read.data]);

  const save = useMutation({
    mutationFn: () => Memory.write(selected as string, draft),
    onSuccess: () => {
      setErr(null);
      qc.invalidateQueries({ queryKey: ['memory'] });
    },
    onError: (e) =>
      setErr(e instanceof ApiError ? JSON.stringify(e.payload) : (e as Error).message),
  });

  return (
    <Page title="Memory">
      <p className="text-[11px] font-mono text-black/55 dark:text-white/55">
        {list.data?.root}
        {list.data?.exists === false && ' (does not exist yet)'}
      </p>
      <div className="grid grid-cols-1 md:grid-cols-[260px_1fr] gap-4">
        <Card>
          {list.isPending && <p className="text-xs">Loading…</p>}
          <ul className="text-sm">
            {(list.data?.entries ?? []).map((e) => (
              <li
                key={e.path}
                onClick={() => setSelected(e.path)}
                className={`cursor-pointer truncate px-2 py-1 rounded hover:bg-black/5 dark:hover:bg-white/10 ${
                  selected === e.path ? 'bg-sky-500/15 text-sky-700 dark:text-sky-300' : ''
                }`}
              >
                📝 {e.path}
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          {!selected && (
            <p className="text-xs text-black/60 dark:text-white/60">Select a memory file.</p>
          )}
          {selected && (
            <>
              <div className="flex items-center justify-between mb-2">
                <p className="text-[11px] font-mono truncate">{selected}</p>
                <button
                  onClick={() => save.mutate()}
                  disabled={save.isPending}
                  className="rounded-md bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white text-xs px-3 py-1"
                >
                  {save.isPending ? 'Saving…' : 'Save'}
                </button>
              </div>
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                className="w-full h-[60vh] rounded border border-black/10 dark:border-white/15 bg-black/[0.02] dark:bg-white/[0.03] p-2 font-mono text-xs"
              />
              <ErrorMsg>{err}</ErrorMsg>
            </>
          )}
        </Card>
      </div>
    </Page>
  );
}
