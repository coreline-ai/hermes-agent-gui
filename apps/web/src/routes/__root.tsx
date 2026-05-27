import { createRootRoute, Link, Outlet } from '@tanstack/react-router';
import { useEffect } from 'react';
import { useAuthStore } from '@/stores/auth-store';
import { GlobalNav } from '@/components/global-nav';
import { GlobalSearch } from '@/components/global-search';
import { UpdaterToast } from '@/components/updater-toast';
import { useT } from '@/lib/i18n';
import { useSessionEvents } from '@/hooks/use-session-events';

export const Route = createRootRoute({ component: RootLayout });

function RootLayout() {
  const t = useT();
  const status = useAuthStore((s) => s.status);
  const hydrate = useAuthStore((s) => s.hydrate);
  const user = useAuthStore((s) => s.user);
  const doLogout = useAuthStore((s) => s.logout);
  useSessionEvents(status === 'authenticated');

  useEffect(() => {
    if (status === 'unknown') void hydrate();
  }, [status, hydrate]);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-black/5 dark:border-white/10 px-4 py-3 flex items-center justify-between">
        <Link to="/" className="flex flex-col">
          <span className="text-sm font-semibold tracking-tight">{t('app.title')}</span>
          <span className="text-[10px] text-black/60 dark:text-white/60">{t('app.subtitle')}</span>
        </Link>
        {status === 'authenticated' && (
          <div className="flex items-center gap-3 text-xs">
            <span className="text-black/60 dark:text-white/60">{user?.name}</span>
            <button onClick={() => void doLogout()} className="hover:underline">
              {t('auth.signOut')}
            </button>
          </div>
        )}
      </header>
      <GlobalNav />
      {status === 'authenticated' && <GlobalSearch />}
      <main className="flex-1 px-4 py-6">
        <Outlet />
      </main>
      <UpdaterToast />
    </div>
  );
}
