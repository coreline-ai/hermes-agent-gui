import { type ReactNode } from 'react';

export function Page({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="max-w-5xl mx-auto space-y-5">
      <header className="flex items-center justify-between gap-3">
        <h2 className="text-xl font-semibold">{title}</h2>
        {action}
      </header>
      {children}
    </section>
  );
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-lg border border-black/5 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.03] p-4 ${className}`}>
      {children}
    </div>
  );
}

export function ErrorMsg({ children }: { children: ReactNode }) {
  if (!children) return null;
  return (
    <p role="alert" className="text-xs text-rose-600 dark:text-rose-400">
      {children}
    </p>
  );
}
