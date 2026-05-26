import { useT } from '@/lib/i18n';

export function QrCodeFlow({ hint }: { hint?: string }) {
  const t = useT();
  return (
    <div className="rounded-lg border border-dashed border-black/15 dark:border-white/20 p-3 text-xs text-black/60 dark:text-white/60">
      <div className="mb-2 flex h-24 w-24 items-center justify-center rounded-md bg-white text-black shadow-inner" aria-hidden="true">
        <span className="text-2xl">▦</span>
      </div>
      <p className="font-medium text-black/75 dark:text-white/75">{t('messaging.qr.title')}</p>
      <p className="mt-1">{hint || t('messaging.qr.help')}</p>
    </div>
  );
}
