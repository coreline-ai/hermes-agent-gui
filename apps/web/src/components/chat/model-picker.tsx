import { useQueries, useQuery } from '@tanstack/react-query';
import { Providers } from '@/lib/api';

export function ModelPicker({ value, onChange, profile = 'default' }: { value: string; onChange: (model: string) => void; profile?: string }) {
  const providers = useQuery({ queryKey: ['providers'], queryFn: Providers.list });
  const enabled = (providers.data?.providers ?? []).filter((provider) => provider.enabled);
  const modelQueries = useQueries({
    queries: enabled.slice(0, 8).map((provider) => ({
      queryKey: ['provider-models', provider.id],
      queryFn: () => Providers.models(provider.id),
      staleTime: 300_000,
    })),
  });

  const options = enabled.flatMap((provider, index) => {
    const models = modelQueries[index]?.data?.models ?? [];
    return models.map((model) => ({
      value: `${provider.label}:${model.id}`,
      model: model.id,
      provider: provider.label,
    }));
  });

  return (
    <label className="flex items-center gap-2 text-xs">
      <span className="text-black/55 dark:text-white/55">Model · {profile}</span>
      <select
        aria-label="Model picker"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="max-w-[220px] rounded-md border border-black/10 bg-transparent px-2 py-1 text-xs outline-none focus:ring-2 focus:ring-sky-500/40 dark:border-white/15"
      >
        <option value="auto">auto</option>
        {options.map((option) => (
          <option key={option.value} value={option.model}>
            {option.provider} · {option.model}
          </option>
        ))}
      </select>
    </label>
  );
}
