import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { ApiError, Persona } from '@/lib/api';

export const Route = createFileRoute('/persona')({
  beforeLoad: requireAuth,
  component: PersonaPage,
});

function errorText(error: unknown): string {
  if (error instanceof ApiError && error.payload && typeof error.payload === 'object') {
    const payload = error.payload as Record<string, unknown>;
    return String(payload.detail ?? payload.error ?? error.message);
  }
  return error instanceof Error ? error.message : String(error);
}

function PersonaPage() {
  const qc = useQueryClient();
  const persona = useQuery({ queryKey: ['persona'], queryFn: () => Persona.get() });
  const presets = useQuery({ queryKey: ['persona-presets'], queryFn: Persona.presets });
  const [soul, setSoul] = useState('');
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (persona.data) setSoul(persona.data.soul_md);
  }, [persona.data]);

  const saveMut = useMutation({
    mutationFn: () => Persona.save(soul),
    onSuccess: () => {
      setError(null);
      setNotice('Persona saved.');
      void qc.invalidateQueries({ queryKey: ['persona'] });
    },
    onError: (err) => setError(errorText(err)),
  });

  return (
    <Page title="Persona SOUL" action={<span className="text-xs text-black/55 dark:text-white/55">SOUL.md · 100KB max</span>}>
      <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
        <Card>
          <h3 className="mb-3 text-sm font-semibold">Presets</h3>
          <div className="space-y-2">
            {(presets.data?.presets ?? []).map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => setSoul(preset.soul_md)}
                className="w-full rounded-lg border border-black/5 p-3 text-left hover:bg-sky-500/10 focus:bg-sky-500/10 focus:outline-none dark:border-white/10"
              >
                <p className="text-sm font-medium">{preset.label}</p>
                <p className="mt-1 line-clamp-2 text-xs text-black/55 dark:text-white/55">{preset.soul_md}</p>
              </button>
            ))}
          </div>
        </Card>
        <Card>
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">Profile: {persona.data?.profile_name ?? 'default'}</h3>
              <p className="text-[10px] text-black/55 dark:text-white/55">
                {soul.length.toLocaleString()} chars · {persona.data?.updated_at ? new Date(persona.data.updated_at * 1000).toLocaleString() : 'not saved yet'}
              </p>
            </div>
            <button
              type="button"
              disabled={saveMut.isPending || soul.length > 100 * 1024}
              onClick={() => saveMut.mutate()}
              className="rounded-md bg-sky-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-700 disabled:opacity-50"
            >
              Apply
            </button>
          </div>
          <textarea
            value={soul}
            onChange={(event) => setSoul(event.target.value)}
            rows={22}
            className="w-full rounded-lg border border-black/10 bg-transparent p-3 font-mono text-xs leading-5 outline-none focus:ring-2 focus:ring-sky-500/40 dark:border-white/15"
          />
          {soul.length > 100 * 1024 && <ErrorMsg>SOUL.md is larger than 100KB.</ErrorMsg>}
          <ErrorMsg>{error}</ErrorMsg>
          {notice && <p className="mt-2 text-xs text-emerald-700 dark:text-emerald-300" role="status">{notice}</p>}
        </Card>
      </div>
    </Page>
  );
}
