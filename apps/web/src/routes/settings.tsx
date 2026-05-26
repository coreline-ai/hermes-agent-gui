import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery } from '@tanstack/react-query';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card } from '@/components/page';
import { AuthMaintenance } from '@/lib/api';
import { useThemeStore, THEMES, type Theme } from '@/stores/theme-store';
import { useLocaleStore, LOCALES, type Locale, useT } from '@/lib/i18n';

export const Route = createFileRoute('/settings')({
  beforeLoad: requireAuth,
  component: SettingsPage,
});

function SettingsPage() {
  const t = useT();
  const { theme, setTheme } = useThemeStore();
  const { locale, setLocale } = useLocaleStore();
  const locks = useQuery({ queryKey: ['login-locks'], queryFn: AuthMaintenance.loginLocks });
  const clearLocks = useMutation({
    mutationFn: (ip?: string) => AuthMaintenance.clearLoginLocks(ip),
    onSuccess: () => locks.refetch(),
  });

  return (
    <Page title="Settings">
      <Card>
        <h3 className="mb-2 text-sm font-medium">{t('theme.label')}</h3>
        <div className="flex flex-wrap gap-2">
          {THEMES.map((th) => (
            <button key={th} onClick={() => setTheme(th as Theme)} className={`rounded-md border px-3 py-1.5 text-xs ${theme === th ? 'border-sky-500 bg-sky-500/15 text-sky-700 dark:text-sky-300' : 'border-black/10 dark:border-white/15'}`}>
              {t(`theme.${th}`)}
            </button>
          ))}
        </div>
      </Card>

      <Card>
        <h3 className="mb-2 text-sm font-medium">Language</h3>
        <div className="flex gap-2">
          {LOCALES.map((l) => (
            <button key={l} onClick={() => setLocale(l as Locale)} className={`rounded-md border px-3 py-1.5 text-xs ${locale === l ? 'border-sky-500 bg-sky-500/15 text-sky-700 dark:text-sky-300' : 'border-black/10 dark:border-white/15'}`}>
              {l === 'en' ? 'English' : '한국어'}
            </button>
          ))}
        </div>
      </Card>

      <Card>
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-medium">Login locks</h3>
            <p className="text-xs text-black/55 dark:text-white/55">Per-IP failed login buckets can be cleared without restarting.</p>
          </div>
          <button onClick={() => clearLocks.mutate(undefined)} className="rounded-md bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-900 disabled:opacity-50" disabled={clearLocks.isPending}>Clear all</button>
        </div>
        <ul className="space-y-2 text-sm">
          {(locks.data?.locks ?? []).map((lock) => (
            <li key={lock.ip} className="flex items-center justify-between rounded-md bg-black/[0.03] px-3 py-2 dark:bg-white/[0.04]">
              <span className="font-mono text-xs">{lock.ip} · {lock.attempts} attempts</span>
              <button onClick={() => clearLocks.mutate(lock.ip)} className="text-xs text-rose-600 hover:underline dark:text-rose-400">unlock</button>
            </li>
          ))}
          {locks.data?.locks.length === 0 && <li className="text-xs text-black/55 dark:text-white/55">No locked IPs.</li>}
        </ul>
      </Card>
    </Page>
  );
}
