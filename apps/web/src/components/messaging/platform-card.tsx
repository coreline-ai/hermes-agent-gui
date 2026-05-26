import type { PlatformMeta } from '@/lib/api';
import { useT } from '@/lib/i18n';
import { StatusBadge } from './status-badge';

export function PlatformCard({ platform, selected, onSelect }: { platform: PlatformMeta; selected?: boolean; onSelect: () => void }) {
  const t = useT();
  const label = t(`messaging.platform.${platform.id}.label`);
  const help = t(`messaging.platform.${platform.id}.help`);
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      aria-label={t('messaging.card.open', { platform: label })}
      className={`group text-left rounded-xl border p-4 transition focus:outline-none focus:ring-2 focus:ring-sky-500/50 ${
        selected
          ? 'border-sky-500 bg-sky-500/10 shadow-sm'
          : 'border-black/5 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.03] hover:border-sky-500/40 hover:bg-sky-500/5'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{label}</p>
          <p className="mt-1 line-clamp-2 text-xs leading-5 text-black/60 dark:text-white/60">{help}</p>
        </div>
        <StatusBadge configured={platform.configured} connected={platform.connected} lastError={platform.last_error} />
      </div>
      <div className="mt-3 flex items-center justify-between gap-2">
        <span
          className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
            platform.mode === 'direct'
              ? 'bg-violet-500/15 text-violet-700 dark:text-violet-300'
              : 'bg-slate-500/15 text-slate-700 dark:text-slate-300'
          }`}
        >
          {platform.mode === 'direct' ? t('messaging.mode.direct') : t('messaging.mode.delegated')}
        </span>
        <span className="text-[10px] text-black/45 dark:text-white/45 group-hover:text-sky-600 dark:group-hover:text-sky-300">
          {t('messaging.card.configure')}
        </span>
      </div>
    </button>
  );
}
