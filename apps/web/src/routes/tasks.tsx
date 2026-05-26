import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { Tasks, type TaskLane, type TaskRow, ApiError } from '@/lib/api';

export const Route = createFileRoute('/tasks')({
  beforeLoad: requireAuth,
  component: TasksPage,
});

const LANES: TaskLane[] = ['backlog', 'ready', 'running', 'review', 'blocked', 'needs_you', 'done'];

function TasksPage() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ['tasks'], queryFn: Tasks.list });
  const [title, setTitle] = useState('');
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () => Tasks.create(title, 'backlog'),
    onSuccess: () => {
      setTitle('');
      void qc.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: (e) =>
      setError(e instanceof ApiError ? JSON.stringify(e.payload) : (e as Error).message),
  });
  const update = useMutation({
    mutationFn: ({ id, lane }: { id: string; lane: TaskLane }) => Tasks.update(id, { lane }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  });
  const remove = useMutation({
    mutationFn: (id: string) => Tasks.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  });

  const byLane = list.data?.by_lane;

  return (
    <Page title="Tasks">
      <Card>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (title.trim()) create.mutate();
          }}
          className="flex gap-2"
        >
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Task title…"
            className="flex-1 rounded-md border border-black/10 dark:border-white/15 bg-transparent px-3 py-1.5 text-sm"
          />
          <button
            type="submit"
            disabled={create.isPending}
            className="rounded-md bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white text-sm px-3 py-1.5"
          >
            New
          </button>
        </form>
        <ErrorMsg>{error}</ErrorMsg>
      </Card>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {LANES.map((lane) => {
          const rows: TaskRow[] = byLane?.[lane] ?? [];
          return (
            <Card key={lane} className="min-h-[120px]">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-semibold uppercase tracking-wide">{lane}</h3>
                <span className="text-[10px] text-black/55 dark:text-white/55">{rows.length}</span>
              </div>
              <ul className="space-y-1.5">
                {rows.map((t) => (
                  <li
                    key={t.id}
                    className="rounded-md border border-black/5 dark:border-white/10 px-2 py-1.5 text-xs"
                  >
                    <p className="truncate">{t.title}</p>
                    <div className="mt-1 flex items-center gap-1">
                      <select
                        value={t.lane}
                        onChange={(e) => update.mutate({ id: t.id, lane: e.target.value as TaskLane })}
                        className="text-[10px] bg-transparent border border-black/10 dark:border-white/15 rounded px-1 py-0.5"
                      >
                        {LANES.map((l) => (
                          <option key={l} value={l}>
                            {l}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={() => remove.mutate(t.id)}
                        className="text-[10px] text-rose-600 dark:text-rose-400 hover:underline ml-auto"
                      >
                        del
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          );
        })}
      </div>
    </Page>
  );
}
