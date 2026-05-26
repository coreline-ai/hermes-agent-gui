import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { Backup, Groups, type Group } from '@/lib/api';

export const Route = createFileRoute('/groups')({
  beforeLoad: requireAuth,
  component: GroupsPage,
});

function GroupsPage() {
  const qc = useQueryClient();
  const groups = useQuery({ queryKey: ['groups'], queryFn: Groups.list });
  const [selected, setSelected] = useState<string | null>(null);
  const [name, setName] = useState('Research Room');
  const [participants, setParticipants] = useState('Researcher, Coder');
  const [message, setMessage] = useState('@Researcher summarize this decision');
  const [error, setError] = useState<string | null>(null);

  const detail = useQuery({
    queryKey: ['groups', selected],
    queryFn: () => Groups.get(selected as string),
    enabled: Boolean(selected),
  });

  const create = useMutation({
    mutationFn: () => Groups.create({
      name,
      participants: participants.split(',').map((item) => ({ name: item.trim(), profile: 'default', model: 'auto' })).filter((item) => item.name),
    }),
    onSuccess: (group) => {
      setSelected(group.id);
      setError(null);
      void qc.invalidateQueries({ queryKey: ['groups'] });
    },
    onError: (err) => setError(err instanceof Error ? err.message : 'create failed'),
  });

  const send = useMutation({
    mutationFn: () => Groups.send(selected as string, message),
    onSuccess: () => {
      setError(null);
      void detail.refetch();
    },
    onError: (err) => setError(err instanceof Error ? err.message : 'send failed'),
  });

  function onCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    create.mutate();
  }

  const current = detail.data;

  return (
    <Page title="Group Chat" action={<div className="flex gap-2 text-xs"><a href={Backup.exportUrl()} className="underline">Backup</a><a href={Backup.debugDumpUrl()} className="underline">Debug dump</a></div>}>
      <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
        <Card className="space-y-3">
          <form onSubmit={onCreate} className="space-y-2">
            <input value={name} onChange={(e) => setName(e.target.value)} className="w-full rounded-md border border-black/10 bg-transparent px-3 py-2 text-sm dark:border-white/15" />
            <input value={participants} onChange={(e) => setParticipants(e.target.value)} className="w-full rounded-md border border-black/10 bg-transparent px-3 py-2 text-sm dark:border-white/15" />
            <button className="rounded-md bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50" disabled={create.isPending}>Create group</button>
          </form>
          <ErrorMsg>{error}</ErrorMsg>
          <ul className="space-y-2">
            {(groups.data?.groups ?? []).map((group) => (
              <GroupRow key={group.id} group={group} active={selected === group.id} onClick={() => setSelected(group.id)} />
            ))}
          </ul>
        </Card>

        <Card className="space-y-4">
          {!current && <p className="text-sm text-black/55 dark:text-white/55">Create or select a group to route @mentions.</p>}
          {current && (
            <>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="font-semibold">{current.name}</h3>
                  <p className="font-mono text-[11px] text-black/50 dark:text-white/50">Invite {current.invite_code}</p>
                </div>
                <div className="flex gap-1">
                  {current.participants.map((p) => <span key={p.name} className="rounded-full bg-black/5 px-2 py-1 text-xs dark:bg-white/10">@{p.name}</span>)}
                </div>
              </div>
              <div className="space-y-2 rounded-lg border border-black/5 p-3 dark:border-white/10">
                {(current.messages ?? []).map((item) => (
                  <div key={item.id} className="text-sm"><span className="font-semibold text-sky-600">{item.participant}</span> · {item.content}</div>
                ))}
                {current.messages.length === 0 && <p className="text-xs text-black/55 dark:text-white/55">No messages yet.</p>}
              </div>
              <form onSubmit={(e) => { e.preventDefault(); send.mutate(); }} className="flex gap-2">
                <input value={message} onChange={(e) => setMessage(e.target.value)} className="flex-1 rounded-md border border-black/10 bg-transparent px-3 py-2 text-sm dark:border-white/15" />
                <button disabled={!message.trim() || send.isPending} className="rounded-md bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50">Route</button>
              </form>
            </>
          )}
        </Card>
      </div>
    </Page>
  );
}

function GroupRow({ group, active, onClick }: { group: Group; active: boolean; onClick: () => void }) {
  return (
    <li>
      <button onClick={onClick} className={`w-full rounded-md px-3 py-2 text-left text-sm hover:bg-black/5 dark:hover:bg-white/10 ${active ? 'bg-sky-500/15 text-sky-700 dark:text-sky-300' : ''}`}>
        <span className="block font-medium">{group.name}</span>
        <span className="text-[11px] text-black/50 dark:text-white/50">{group.participants.length} participants</span>
      </button>
    </li>
  );
}
