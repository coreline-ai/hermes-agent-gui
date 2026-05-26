import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { Mcp, ApiError } from '@/lib/api';

export const Route = createFileRoute('/mcp')({
  beforeLoad: requireAuth,
  component: McpPage,
});

function McpPage() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ['mcp'], queryFn: Mcp.list });
  const [name, setName] = useState('');
  const [cmd, setCmd] = useState('');
  const [error, setError] = useState<string | null>(null);

  const add = useMutation({
    mutationFn: () => Mcp.add({ name, command: cmd.split(/\s+/).filter(Boolean) }),
    onSuccess: () => {
      setName('');
      setCmd('');
      setError(null);
      void qc.invalidateQueries({ queryKey: ['mcp'] });
    },
    onError: (e) =>
      setError(e instanceof ApiError ? JSON.stringify(e.payload) : (e as Error).message),
  });

  const remove = useMutation({
    mutationFn: (n: string) => Mcp.remove(n),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mcp'] }),
  });

  return (
    <Page title="MCP servers" action={<span className="text-[10px] text-black/50 dark:text-white/50">source: {list.data?.source ?? '…'}</span>}>
      <Card>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (name.trim() && cmd.trim()) add.mutate();
          }}
          className="grid grid-cols-1 sm:grid-cols-[180px_1fr_auto] gap-2"
        >
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="name"
            className="rounded-md border border-black/10 dark:border-white/15 bg-transparent px-3 py-1.5 text-sm"
          />
          <input
            value={cmd}
            onChange={(e) => setCmd(e.target.value)}
            placeholder="command + args (space-separated)"
            className="rounded-md border border-black/10 dark:border-white/15 bg-transparent px-3 py-1.5 text-sm font-mono"
          />
          <button
            type="submit"
            disabled={add.isPending}
            className="rounded-md bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white text-sm px-3 py-1.5"
          >
            Add
          </button>
        </form>
        <ErrorMsg>{error}</ErrorMsg>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {(list.data?.servers ?? []).map((s) => (
          <Card key={s.name}>
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium">{s.name}</h3>
              <button
                onClick={() => remove.mutate(s.name)}
                className="text-xs text-rose-600 dark:text-rose-400 hover:underline"
              >
                remove
              </button>
            </div>
            <p className="mt-1 text-[11px] font-mono text-black/70 dark:text-white/70 break-all">
              {s.command.join(' ')}
            </p>
          </Card>
        ))}
        {list.data && list.data.servers.length === 0 && (
          <p className="text-xs text-black/60 dark:text-white/60">No MCP servers registered.</p>
        )}
      </div>
    </Page>
  );
}
