import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { Marketplace } from '@/lib/api';

export const Route = createFileRoute('/marketplace')({ beforeLoad: requireAuth, component: MarketplacePage });

function MarketplacePage() {
  const qc = useQueryClient();
  const [q, setQ] = useState('');
  const [error, setError] = useState<string | null>(null);
  const catalog = useQuery({ queryKey: ['marketplace', q], queryFn: () => Marketplace.catalog(q) });
  const install = useMutation({
    mutationFn: (id: string) => Marketplace.install(id),
    onSuccess: () => {
      setError(null);
      void qc.invalidateQueries({ queryKey: ['marketplace'] });
    },
    onError: (err) => setError(err instanceof Error ? err.message : 'install failed'),
  });
  const categories = Array.from(new Set((catalog.data?.items ?? []).map((item) => item.category))).sort();
  return (
    <Page title="Agent Marketplace" action={<span className="text-xs text-black/55 dark:text-white/55">30 curated personas · one-click install</span>}>
      <Card>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search presets…" className="w-full rounded-md border border-black/10 bg-transparent px-3 py-2 text-sm dark:border-white/15" />
        <ErrorMsg>{error}</ErrorMsg>
      </Card>
      {categories.map((category) => (
        <section key={category} className="space-y-2">
          <h3 className="text-sm font-semibold capitalize">{category}</h3>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {(catalog.data?.items ?? []).filter((item) => item.category === category).map((item) => (
              <Card key={item.id} className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div><h4 className="font-semibold">{item.label}</h4><p className="text-xs text-black/55 dark:text-white/55">{item.tags.join(' · ')}</p></div>
                  {item.installed && <span className="rounded-full bg-emerald-500/10 px-2 py-1 text-[10px] text-emerald-700 dark:text-emerald-300">installed</span>}
                </div>
                <p className="line-clamp-3 text-sm text-black/65 dark:text-white/65">{item.soul_md.replace(/^#.*\n+/, '')}</p>
                <button onClick={() => install.mutate(item.id)} disabled={item.installed || install.isPending} className="rounded-md bg-sky-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-700 disabled:opacity-50">{item.installed ? item.install?.profile : 'Install'}</button>
              </Card>
            ))}
          </div>
        </section>
      ))}
    </Page>
  );
}
