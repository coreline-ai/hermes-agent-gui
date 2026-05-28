import { createFileRoute } from '@tanstack/react-router';
import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { BrowserUse } from '@/lib/api';

export const Route = createFileRoute('/browser')({
  beforeLoad: requireAuth,
  component: BrowserPage,
});

function BrowserPage() {
  const [url, setUrl] = useState('https://example.com');
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [selector, setSelector] = useState('title');
  const [extracted, setExtracted] = useState('');
  const [error, setError] = useState<string | null>(null);
  const nav = useMutation({
    mutationFn: () => BrowserUse.navigate(url, sessionId),
    onSuccess: (data) => {
      setSessionId(data.session_id);
      setExtracted(data.title);
      setError(null);
    },
    onError: (err) => setError(err instanceof Error ? err.message : 'navigate failed'),
  });
  const extract = useMutation({
    mutationFn: () => BrowserUse.extract(sessionId as string, selector),
    onSuccess: (data) => {
      setExtracted(data.text);
      setError(null);
    },
    onError: (err) => setError(err instanceof Error ? err.message : 'extract failed'),
  });

  return (
    <Page title="Browser Use" action={<span className="text-xs text-black/55 dark:text-white/55">HTTP fallback · allowlist + private IP guard</span>}>
      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <Card className="space-y-3">
          <input value={url} onChange={(e) => setUrl(e.target.value)} className="w-full rounded-md border border-black/10 bg-transparent px-3 py-2 text-sm dark:border-white/15" />
          <button onClick={() => nav.mutate()} disabled={nav.isPending} className="rounded-md bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50">Navigate</button>
          <input value={selector} onChange={(e) => setSelector(e.target.value)} className="w-full rounded-md border border-black/10 bg-transparent px-3 py-2 text-sm dark:border-white/15" />
          <button onClick={() => extract.mutate()} disabled={!sessionId || extract.isPending} className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-50">Extract</button>
          <ErrorMsg>{error}</ErrorMsg>
        </Card>
        <Card>
          <p className="font-mono text-[11px] text-black/50 dark:text-white/50">Session {sessionId ?? '—'}</p>
          <h3 className="mt-2 text-lg font-semibold">{nav.data?.title || 'No page loaded'}</h3>
          {nav.data?.screenshot_b64 && <div className="mt-4 rounded-lg border border-dashed border-black/10 p-8 text-center text-xs text-black/55 dark:border-white/15 dark:text-white/55">Screenshot placeholder from dependency-free fallback · {nav.data.screenshot_b64.length} bytes b64</div>}
          {extracted && <pre className="mt-4 whitespace-pre-wrap rounded bg-black/[0.03] p-3 text-xs dark:bg-white/[0.04]">{extracted}</pre>}
        </Card>
      </div>
    </Page>
  );
}
