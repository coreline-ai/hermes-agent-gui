import { createFileRoute } from '@tanstack/react-router';
import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { Terminal, type ExecResult, ApiError } from '@/lib/api';

export const Route = createFileRoute('/terminal')({
  beforeLoad: requireAuth,
  component: TerminalPage,
});

function TerminalPage() {
  const status = useQuery({ queryKey: ['terminal-status'], queryFn: Terminal.status });
  const [cmd, setCmd] = useState('pwd');
  const [cwd, setCwd] = useState('.');
  const [allowUnsafe, setAllowUnsafe] = useState(false);
  const [history, setHistory] = useState<{ cmd: string; result: ExecResult | { error: string } }[]>([]);
  const enabled = status.data?.exec_available === true;
  const controlsDisabled = !enabled || status.isLoading;
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
    <Page title="Terminal" action={<span className="text-xs text-black/55 dark:text-white/55">Local command gate</span>}>
      {status.isError && (
        <ErrorMsg>{status.error instanceof Error ? status.error.message : '터미널 상태를 불러오지 못했습니다.'}</ErrorMsg>
      )}

      {status.isSuccess && !enabled && (
        <Card className="border-amber-500/25 bg-amber-500/10">
          <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-200">터미널 실행이 비활성화되어 있습니다</h3>
          <p className="mt-2 text-sm text-amber-800/80 dark:text-amber-100/80">
            보안 기본값 때문에 Electron에서도 명령 실행은 자동으로 켜지지 않습니다. 로컬에서 터미널을 쓰려면 앱을 아래처럼 다시 실행하세요.
          </p>
          <pre className="mt-3 overflow-x-auto rounded-md bg-black/10 p-3 text-xs dark:bg-white/10">
{`env -u ELECTRON_RUN_AS_NODE \
HERMES_GUI_PASSWORD=<your-password> \
HERMES_GUI_FAKE_BACKEND=echo \
HERMES_GUI_ENABLE_EXEC=1 \
npm --prefix electron run dev`}
          </pre>
        </Card>
      )}

      <Card>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (cmd.trim() && !controlsDisabled) exec.mutate();
          }}
          className="space-y-3"
        >
          <div className="grid gap-2 md:grid-cols-[160px_1fr_auto]">
            <input
              value={cwd}
              onChange={(e) => setCwd(e.target.value)}
              className="rounded-md border border-black/10 bg-transparent px-2 py-1.5 font-mono text-xs dark:border-white/15"
              placeholder="cwd"
              disabled={controlsDisabled}
            />
            <input
              value={cmd}
              onChange={(e) => setCmd(e.target.value)}
              className="rounded-md border border-black/10 bg-transparent px-3 py-1.5 font-mono text-sm dark:border-white/15"
              placeholder="pwd"
              disabled={controlsDisabled}
            />
            <button
              type="submit"
              disabled={controlsDisabled || exec.isPending || !cmd.trim()}
              className="rounded-md bg-sky-600 px-3 py-1.5 text-sm text-white hover:bg-sky-700 disabled:opacity-50"
            >
              Run
            </button>
          </div>
          <label className={`flex items-center gap-2 text-[11px] ${controlsDisabled ? 'text-black/35 dark:text-white/35' : 'text-black/60 dark:text-white/60'}`}>
            <input
              type="checkbox"
              checked={allowUnsafe}
              disabled={controlsDisabled}
              onChange={(e) => setAllowUnsafe(e.target.checked)}
            />
            allow non-allowlisted command — 로컬 개발 전용 고급 옵션
          </label>
        </form>
      </Card>

      <Card>
        <h3 className="mb-2 text-sm font-semibold">Allowed commands</h3>
        <p className="text-xs leading-relaxed text-black/60 dark:text-white/60">
          {(status.data?.allowlist ?? []).join(' · ') || 'Loading…'}
        </p>
        <p className="mt-2 text-[11px] text-black/45 dark:text-white/45">{status.data?.detail}</p>
      </Card>

      <div className="space-y-2">
        {history.map((entry, i) => (
          <Card key={`${entry.cmd}-${i}`}>
            <p className="mb-1 font-mono text-xs">$ {entry.cmd}</p>
            {'error' in entry.result ? (
              <ErrorMsg>{entry.result.error}</ErrorMsg>
            ) : (
              <pre className="whitespace-pre-wrap break-all text-[11px]">
                {entry.result.stdout}
                {entry.result.stderr && (
                  <span className="text-rose-600 dark:text-rose-400">{entry.result.stderr}</span>
                )}
                <span className="text-[10px] text-black/50 dark:text-white/50">
                  {'\n'}exit {entry.result.exit_code}
                  {entry.result.truncated && ' (truncated)'} · {entry.result.cwd}
                </span>
              </pre>
            )}
          </Card>
        ))}
      </div>
    </Page>
  );
}
