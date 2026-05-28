import { useQueries, useQuery } from '@tanstack/react-query';
import { Providers } from '@/lib/api';

export interface ModelSelection {
  providerId: string;
  model: string;
}

function encodeSelection(selection: ModelSelection): string {
  return `${selection.providerId}::${selection.model}`;
}

function decodeSelection(value: string): ModelSelection {
  const [providerId = 'auto', ...modelParts] = value.split('::');
  return { providerId, model: modelParts.join('::') || 'auto' };
}

export function ModelPicker({
  value,
  onChange,
  profile = 'default',
}: {
  value: ModelSelection;
  onChange: (selection: ModelSelection) => void;
  profile?: string;
}) {
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
      value: encodeSelection({ providerId: provider.id, model: model.id }),
      model: model.id,
      provider: provider.label,
    }));
  });

  return (
    <label className="flex items-center gap-2 text-xs">
      <span className="text-black/55 dark:text-white/55">Model · {profile}</span>
      <select
        aria-label="Model picker"
        value={encodeSelection(value)}
        onChange={(event) => onChange(decodeSelection(event.target.value))}
        className="max-w-[220px] rounded-md border border-black/10 bg-transparent px-2 py-1 text-xs outline-none focus:ring-2 focus:ring-sky-500/40 dark:border-white/15"
      >
        <option value="auto::auto">auto</option>
        {value.providerId === 'auto' && value.model !== 'auto' && (
          <option value={encodeSelection(value)}>manual · {value.model}</option>
        )}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.provider} · {option.model}
          </option>
        ))}
      </select>
    </label>
  );
}
