import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { ApiError, Providers, type ProviderKind, type ProviderPreset } from '@/lib/api';

export const Route = createFileRoute('/providers')({
  beforeLoad: requireAuth,
  component: ProvidersPage,
});

function errorText(error: unknown): string {
  if (error instanceof ApiError && error.payload && typeof error.payload === 'object') {
    const payload = error.payload as Record<string, unknown>;
    return String(payload.detail ?? payload.error ?? error.message);
  }
  return error instanceof Error ? error.message : String(error);
}

function ProvidersPage() {
  const qc = useQueryClient();
  const presets = useQuery({ queryKey: ['provider-presets'], queryFn: Providers.presets });
  const providers = useQuery({ queryKey: ['providers'], queryFn: Providers.list });
  const [kind, setKind] = useState<ProviderKind>('openai');
  const selectedPreset = useMemo(
    () => presets.data?.presets.find((preset) => preset.kind === kind),
    [kind, presets.data?.presets],
  );
  const [label, setLabel] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const createMut = useMutation({
    mutationFn: () =>
      Providers.create({
        kind,
        label: label || selectedPreset?.label || kind,
        base_url: baseUrl || selectedPreset?.base_url,
        api_key: apiKey,
      }),
    onSuccess: () => {
      setLabel('');
      setBaseUrl('');
      setApiKey('');
      setError(null);
      setNotice('Provider added.');
      void qc.invalidateQueries({ queryKey: ['providers'] });
    },
    onError: (err) => setError(errorText(err)),
  });

  return (
    <Page title="Providers" action={<span className="text-xs text-black/55 dark:text-white/55">14 presets + OpenAI-compatible local runtimes</span>}>
      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <Card>
          <h3 className="mb-3 text-sm font-semibold">Add provider</h3>
          <form
            className="space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              createMut.mutate();
            }}
          >
            <label className="block text-xs">
              <span className="mb-1 block font-medium">Preset</span>
              <select
                value={kind}
                onChange={(event) => {
                  const next = event.target.value as ProviderKind;
                  const preset = presets.data?.presets.find((p) => p.kind === next);
                  setKind(next);
                  setBaseUrl(preset?.base_url ?? '');
                  setLabel(preset?.label ?? '');
                }}
                className="w-full rounded-md border border-black/10 bg-transparent px-2 py-1.5 text-xs dark:border-white/15"
              >
                {(presets.data?.presets ?? []).map((preset: ProviderPreset) => (
                  <option key={preset.kind} value={preset.kind}>{preset.label}</option>
                ))}
              </select>
            </label>
            <label className="block text-xs">
              <span className="mb-1 block font-medium">Label</span>
              <input
                value={label}
                placeholder={selectedPreset?.label}
                onChange={(event) => setLabel(event.target.value)}
                className="w-full rounded-md border border-black/10 bg-transparent px-2 py-1.5 text-xs outline-none focus:ring-2 focus:ring-sky-500/40 dark:border-white/15"
              />
            </label>
            <label className="block text-xs">
              <span className="mb-1 block font-medium">Base URL</span>
              <input
                value={baseUrl}
                placeholder={selectedPreset?.base_url}
                onChange={(event) => setBaseUrl(event.target.value)}
                className="w-full rounded-md border border-black/10 bg-transparent px-2 py-1.5 text-xs outline-none focus:ring-2 focus:ring-sky-500/40 dark:border-white/15"
              />
            </label>
            <label className="block text-xs">
              <span className="mb-1 block font-medium">API key {selectedPreset?.auth_type === 'none' ? '(optional)' : ''}</span>
              <input
                type="password"
                value={apiKey}
                placeholder={selectedPreset?.api_key_env}
                onChange={(event) => setApiKey(event.target.value)}
                className="w-full rounded-md border border-black/10 bg-transparent px-2 py-1.5 text-xs outline-none focus:ring-2 focus:ring-sky-500/40 dark:border-white/15"
              />
            </label>
            <button
              type="submit"
              disabled={createMut.isPending}
              className="rounded-md bg-sky-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-700 disabled:opacity-50"
            >
              Add
            </button>
          </form>
          <ErrorMsg>{error}</ErrorMsg>
          {notice && <p className="mt-2 text-xs text-emerald-700 dark:text-emerald-300" role="status">{notice}</p>}
        </Card>

        <Card>
          <h3 className="mb-3 text-sm font-semibold">Configured providers</h3>
          {providers.isPending && <p className="text-xs">Loading…</p>}
          <ul className="divide-y divide-black/5 dark:divide-white/10 -m-4">
            {(providers.data?.providers ?? []).map((provider) => (
              <ProviderRow key={provider.id} id={provider.id} label={provider.label} kind={provider.kind} baseUrl={provider.base_url} status={provider.test_status} />
            ))}
          </ul>
        </Card>
      </div>
    </Page>
  );
}

function ProviderRow({ id, label, kind, baseUrl, status }: { id: string; label: string; kind: string; baseUrl: string; status: string | null }) {
  const qc = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const models = useQuery({ queryKey: ['provider-models', id], queryFn: () => Providers.models(id), enabled: false });
  const testMut = useMutation({
    mutationFn: () => Providers.test(id),
    onSuccess: (result) => {
      setError(null);
      setMessage(`OK · ${result.model_used} · ${result.latency_ms}ms`);
      void qc.invalidateQueries({ queryKey: ['providers'] });
    },
    onError: (err) => setError(errorText(err)),
  });
  return (
    <li className="px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold">{label}</p>
          <p className="truncate text-[10px] text-black/55 dark:text-white/55">{kind} · {baseUrl}</p>
          {status && <p className="mt-1 text-[10px] text-black/50 dark:text-white/50">last test: {status}</p>}
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={() => void models.refetch()}
            className="rounded-md border border-black/10 px-2 py-1 text-[10px] hover:bg-black/5 dark:border-white/15 dark:hover:bg-white/10"
          >
            Models
          </button>
          <button
            type="button"
            disabled={testMut.isPending}
            onClick={() => testMut.mutate()}
            className="rounded-md border border-black/10 px-2 py-1 text-[10px] hover:bg-black/5 disabled:opacity-50 dark:border-white/15 dark:hover:bg-white/10"
          >
            Test
          </button>
        </div>
      </div>
      {models.data && <p className="mt-2 text-xs text-black/65 dark:text-white/65">{models.data.models.map((model) => model.id).join(', ') || 'No models discovered.'}</p>}
      {message && <p className="mt-2 text-xs text-emerald-700 dark:text-emerald-300" role="status">{message}</p>}
      <ErrorMsg>{error}</ErrorMsg>
    </li>
  );
}
