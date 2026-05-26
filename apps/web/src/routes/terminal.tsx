import { createFileRoute } from '@tanstack/react-router';
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { Terminal, type ExecResult, ApiError } from '@/lib/api';

export const Route = createFileRoute('/terminal')({
  beforeLoad: requireAuth,
  component: TerminalPage,
});

function TerminalPage() {
  const [cmd, setCmd] = useState('');
  const [cwd, setCwd] = useState('.');
  const [allowUnsafe, setAllowUnsafe] = useState(false);
  const [history, setHistory] = useState<{ cmd: string; result: ExecResult | { error: string } }[]>([]);
  const exec = useMutation({
    mutationFn: () => Terminal.exec(cmd, cwd, allowUnsafe),
    onSuccess: (result) => {
      setHistory((h) => [...h, { cmd, result }]);
      setCmd('');
    },
    onError: (e) => {
      const detail = e instanceof ApiError ? JSON.stringify(e.payload) : (e as Error).message;
      setHistory((h) => [...h, { cmd, result: { error: detail } }]);
    },
  });

  return (
    <Page title="Terminal">
      <Card>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (cmd.trim()) exec.mutate();
          }}
          className="space-y-2"
        >
          <div className="flex items-center gap-2">
            <input
              value={cwd}
              onChange={(e) => setCwd(e.target.value)}
              className="w-40 rounded-md border border-black/10 dark:border-white/15 bg-transparent px-2 py-1 text-xs font-mono"
              placeholder="cwd"
            />
            <input
              value={cmd}
              onChange={(e) => setCmd(e.target.value)}
              className="flex-1 rounded-md border border-black/10 dark:border-white/15 bg-transparent px-3 py-1.5 text-sm font-mono"
              placeholder="ls -la"
            />
            <button
              type="submit"
              disabled={exec.isPending || !cmd.trim()}
              className="rounded-md bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white text-sm px-3 py-1.5"
            >
              Run
            </button>
          </div>
          <label className="flex items-center gap-1 text-[10px] text-black/60 dark:text-white/60">
            <input
              type="checkbox"
              checked={allowUnsafe}
              onChange={(e) => setAllowUnsafe(e.target.checked)}
            />
            allow_unsafe (bypass allowlist — Phase 3 dev only)
          </label>
        </form>
      </Card>

      {history.length === 0 && (
        <p className="text-xs text-black/60 dark:text-white/60">
          Allowed: <code>ls pwd cat head tail wc grep find echo stat git python3 node pnpm npm</code>
        </p>
      )}

      <div className="space-y-2">
        {history.map((entry, i) => (
          <Card key={i}>
            <p className="text-xs font-mono mb-1">$ {entry.cmd}</p>
            {'error' in entry.result ? (
              <ErrorMsg>{entry.result.error}</ErrorMsg>
            ) : (
              <pre className="text-[11px] whitespace-pre-wrap break-all">
                {entry.result.stdout}
                {entry.result.stderr && (
                  <span className="text-rose-600 dark:text-rose-400">{entry.result.stderr}</span>
                )}
                <span className="text-[10px] text-black/50 dark:text-white/50">
                  {'\n'}exit {entry.result.exit_code}
                  {entry.result.truncated && ' (truncated)'}
                </span>
              </pre>
            )}
          </Card>
        ))}
      </div>
    </Page>
  );
}
