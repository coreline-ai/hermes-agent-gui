import type { PlatformMeta } from '@/lib/api';
import { useT } from '@/lib/i18n';

export function defaultBehavior(platform: PlatformMeta): Record<string, unknown> {
  const out: Record<string, unknown> = { ...platform.behavior };
  for (const [key, spec] of Object.entries(platform.behavior_schema)) {
    if (!(key in out) && 'default' in spec) out[key] = spec.default;
  }
  return out;
}

export function BehaviorEditor({ platform, value, onChange }: { platform: PlatformMeta; value: Record<string, unknown>; onChange: (next: Record<string, unknown>) => void }) {
  const t = useT();
  const entries = Object.entries(platform.behavior_schema);
  if (entries.length === 0) return null;

  function setValue(key: string, next: unknown) {
    onChange({ ...value, [key]: next });
  }

  return (
    <fieldset className="space-y-3 rounded-lg border border-black/5 dark:border-white/10 p-3">
      <legend className="px-1 text-xs font-semibold">{t('messaging.behavior.title')}</legend>
      {entries.map(([key, spec]) => {
        const current = value[key] ?? spec.default;
        if (spec.type === 'boolean') {
          return (
            <label key={key} className="flex items-center justify-between gap-3 text-xs">
              <span>{t(`messaging.behavior.${key}`)}</span>
              <input
                aria-label={t(`messaging.behavior.${key}`)}
                type="checkbox"
                checked={Boolean(current)}
                onChange={(e) => setValue(key, e.target.checked)}
                className="h-4 w-4 rounded border-black/20 text-sky-600"
              />
            </label>
          );
        }
        if (spec.type === 'array') {
          const text = Array.isArray(current) ? current.join(', ') : '';
          return (
            <label key={key} className="block text-xs">
              <span className="mb-1 block font-medium">{t(`messaging.behavior.${key}`)}</span>
              <input
                aria-label={t(`messaging.behavior.${key}`)}
                value={text}
                onChange={(e) => setValue(key, e.target.value.split(',').map((v) => v.trim()).filter(Boolean))}
                placeholder="12345, 67890"
                className="w-full rounded-md border border-black/10 dark:border-white/15 bg-transparent px-2 py-1.5 outline-none focus:ring-2 focus:ring-sky-500/40"
              />
            </label>
          );
        }
        return (
          <label key={key} className="block text-xs">
            <span className="mb-1 block font-medium">{t(`messaging.behavior.${key}`)}</span>
            <input
              aria-label={t(`messaging.behavior.${key}`)}
              value={String(current ?? '')}
              onChange={(e) => setValue(key, e.target.value)}
              className="w-full rounded-md border border-black/10 dark:border-white/15 bg-transparent px-2 py-1.5 outline-none focus:ring-2 focus:ring-sky-500/40"
            />
          </label>
        );
      })}
    </fieldset>
  );
}
