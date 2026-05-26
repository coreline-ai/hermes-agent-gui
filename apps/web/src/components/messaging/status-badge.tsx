import { useT } from '@/lib/i18n';

export function StatusBadge({ configured, connected, lastError }: { configured: boolean; connected: boolean; lastError?: string | null }) {
  const t = useT();
  const label = connected
    ? t('messaging.status.connected')
    : configured
      ? t('messaging.status.configured')
      : t('messaging.status.notConfigured');
  const tone = connected
    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
    : configured
      ? 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300'
      : 'border-black/10 dark:border-white/15 text-black/55 dark:text-white/55';
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${tone}`}
      title={lastError || label}
      aria-label={lastError ? `${label}: ${lastError}` : label}
    >
      {label}
    </span>
  );
}
