import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { Workspace, type WsEntry, ApiError } from '@/lib/api';

export const Route = createFileRoute('/workspace')({
  beforeLoad: requireAuth,
  component: WorkspacePage,
});

function WorkspacePage() {
  const qc = useQueryClient();
  const [path, setPath] = useState('.');
  const [selected, setSelected] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [dirty, setDirty] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const list = useQuery({
    queryKey: ['ws', 'list', path],
    queryFn: () => Workspace.list(path),
  });

  const read = useQuery({
    queryKey: ['ws', 'read', selected],
    queryFn: () => Workspace.read(selected as string),
    enabled: !!selected,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (!selected || !read.data || dirty) return;
    setDraft(read.data.content);
  }, [selected, read.data, dirty]);

  const save = useMutation({
    mutationFn: () => Workspace.write(selected as string, draft),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ws'] });
      setDirty(false);
      setSaveError(null);
    },
    onError: (e) =>
      setSaveError(
        e instanceof ApiError ? `${e.status}: ${JSON.stringify(e.payload)}` : (e as Error).message,
      ),
  });

  return (
    <Page title="Workspace">
      <Card>
        <div className="flex items-center gap-2">
          <input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            className="flex-1 rounded-md border border-black/10 dark:border-white/15 bg-transparent px-3 py-1.5 text-sm outline-none font-mono"
          />
          <button
            onClick={() => qc.invalidateQueries({ queryKey: ['ws', 'list', path] })}
            className="rounded-md border border-black/10 dark:border-white/15 px-3 py-1.5 text-xs"
          >
            refresh
          </button>
        </div>
        {list.error && (
          <ErrorMsg>
            {list.error instanceof ApiError
              ? JSON.stringify(list.error.payload)
              : (list.error as Error).message}
          </ErrorMsg>
        )}
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-[260px_1fr] gap-4">
        <Card>
          {list.isPending && <p className="text-xs">Loading…</p>}
          <ul className="text-sm">
            {(list.data?.entries ?? []).map((e: WsEntry) => (
              <li
                key={e.path}
                onClick={() => {
                  if (e.kind === 'dir') {
                    setPath(e.path);
                    setSelected(null);
                    setDraft('');
                    setDirty(false);
                    setSaveError(null);
                  } else {
                    setSelected(e.path);
                    setDraft('');
                    setDirty(false);
                    setSaveError(null);
                  }
                }}
                className={`cursor-pointer truncate px-2 py-1 rounded hover:bg-black/5 dark:hover:bg-white/10 ${
                  selected === e.path ? 'bg-sky-500/15 text-sky-700 dark:text-sky-300' : ''
                }`}
              >
                {e.kind === 'dir' ? '📁' : '📄'} {e.name}
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          {!selected && (
            <p className="text-xs text-black/60 dark:text-white/60">Select a file on the left.</p>
          )}
          {selected && (
            <>
              <div className="flex items-center justify-between mb-2">
                <p className="text-[11px] font-mono truncate">
                  {selected}
                  {dirty ? ' • unsaved' : ''}
                </p>
                <button
                  onClick={() => save.mutate()}
                  disabled={save.isPending || !read.data}
                  className="rounded-md bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white text-xs px-3 py-1"
                >
                  {save.isPending ? 'Saving…' : 'Save'}
                </button>
              </div>
              {read.isPending && <p className="text-xs">Loading…</p>}
              {read.data && (
                <textarea
                  value={draft}
                  onChange={(e) => {
                    setDraft(e.target.value);
                    setDirty(true);
                  }}
                  className="w-full h-[60vh] rounded border border-black/10 dark:border-white/15 bg-black/[0.02] dark:bg-white/[0.03] p-2 font-mono text-xs"
                />
              )}
              <ErrorMsg>{saveError}</ErrorMsg>
            </>
          )}
        </Card>
      </div>
    </Page>
  );
}
