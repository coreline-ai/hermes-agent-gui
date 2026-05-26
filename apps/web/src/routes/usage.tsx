import { createFileRoute } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card } from '@/components/page';
import { Usage } from '@/lib/api';

export const Route = createFileRoute('/usage')({
  beforeLoad: requireAuth,
  component: UsagePage,
});

const COLORS = ['#0ea5e9', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#64748b'];

function UsagePage() {
  const summary = useQuery({ queryKey: ['usage-summary'], queryFn: () => Usage.summary() });
  const data = summary.data;
  return (
    <Page title="Usage" action={<span className="text-xs text-black/55 dark:text-white/55">30-day token and cost rollup</span>}>
      <div className="grid gap-3 md:grid-cols-4">
        <Stat label="Cost" value={`$${(data?.total_cost_usd ?? 0).toFixed(4)}`} />
        <Stat label="Input tokens" value={(data?.total_input_tokens ?? 0).toLocaleString()} />
        <Stat label="Output tokens" value={(data?.total_output_tokens ?? 0).toLocaleString()} />
        <Stat label="Sessions" value={data?.sessions ?? 0} />
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <Card>
          <h3 className="mb-3 text-sm font-semibold">Daily cost</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data?.daily ?? []}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="cost_usd" fill="#0ea5e9" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <h3 className="mb-3 text-sm font-semibold">Model mix</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data?.by_model ?? []} dataKey="cost_usd" nameKey="model_id" outerRadius={90} label>
                  {(data?.by_model ?? []).map((entry, index) => (
                    <Cell key={entry.model_id} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </Page>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <p className="text-[10px] uppercase tracking-wide text-black/55 dark:text-white/55">{label}</p>
      <p className="mt-1 text-xl font-semibold">{value}</p>
    </Card>
  );
}
