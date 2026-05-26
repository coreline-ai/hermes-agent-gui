import { Link, useRouterState } from '@tanstack/react-router';
import { useAuthStore } from '@/stores/auth-store';
import { useT } from '@/lib/i18n';

const ITEMS = [
  { to: '/chat', key: 'nav.chat' as const },
  { to: '/sessions', key: 'nav.chat' as const, label: 'Sessions' },
  { to: '/workspace', key: 'nav.workspace' as const },
  { to: '/terminal', key: 'nav.chat' as const, label: 'Terminal' },
  { to: '/skills', key: 'nav.skills' as const },
  { to: '/mcp', key: 'nav.mcp' as const },
  { to: '/memory', key: 'nav.memory' as const },
  { to: '/rag', key: 'nav.chat' as const, label: 'RAG' },
  { to: '/messaging', key: 'nav.messaging' as const },
  { to: '/profiles', key: 'nav.profiles' as const },
  { to: '/providers', key: 'nav.providers' as const },
  { to: '/persona', key: 'nav.persona' as const },
  { to: '/usage', key: 'nav.usage' as const },
  { to: '/tasks', key: 'nav.tasks' as const },
  { to: '/cron', key: 'nav.cron' as const },
  { to: '/swarm', key: 'nav.chat' as const, label: 'Swarm' },
  { to: '/groups', key: 'nav.chat' as const, label: 'Groups' },
  { to: '/brain', key: 'nav.chat' as const, label: 'Brain' },
  { to: '/code-graph', key: 'nav.chat' as const, label: 'Code Graph' },
  { to: '/browser', key: 'nav.chat' as const, label: 'Browser' },
  { to: '/office', key: 'nav.chat' as const, label: 'Office' },
  { to: '/cli-bridges', key: 'nav.chat' as const, label: 'CLI' },
  { to: '/marketplace', key: 'nav.chat' as const, label: 'Marketplace' },
  { to: '/dashboard', key: 'nav.dashboard' as const },
  { to: '/settings', key: 'nav.settings' as const },
];

export function GlobalNav() {
  const t = useT();
  const status = useAuthStore((s) => s.status);
  const path = useRouterState({ select: (s) => s.location.pathname });
  if (status !== 'authenticated') return null;

  return (
    <nav className="border-b border-black/5 dark:border-white/10 px-3 py-1.5 overflow-x-auto">
      <ul className="flex gap-1 text-[11px] whitespace-nowrap">
        {ITEMS.map((item) => {
          const active = path === item.to || path.startsWith(`${item.to}/`);
          return (
            <li key={item.to}>
              <Link
                to={item.to}
                className={`px-2 py-1 rounded-md hover:bg-black/5 dark:hover:bg-white/10 ${
                  active ? 'bg-sky-500/15 text-sky-700 dark:text-sky-300' : ''
                }`}
              >
                {item.label ?? t(item.key)}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
