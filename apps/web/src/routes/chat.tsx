import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router';
import { type FormEvent, useRef, useState } from 'react';
import { Virtuoso } from 'react-virtuoso';
import { useAuthStore } from '@/stores/auth-store';
import { ModelPicker } from '@/components/chat/model-picker';
import { PiiRedactedBadge } from '@/components/chat/pii-redacted-badge';
import { SlashMenu } from '@/components/chat/slash-menu';
import { parseSlashCommand, COMMANDS, type SlashCommand } from '@/lib/slash-commands';
import { streamChat, type ChatMessage } from '@/lib/chat-stream';

export const Route = createFileRoute('/chat')({
  beforeLoad: async () => {
    const store = useAuthStore.getState();
    if (store.status === 'unknown') {
      await store.hydrate();
    }
    if (useAuthStore.getState().status !== 'authenticated') {
      throw redirect({ to: '/login' });
    }
  },
  component: ChatPage,
});

interface UiMessage {
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
}

function ChatPage() {
  const user = useAuthStore((s) => s.user);
  const doLogout = useAuthStore((s) => s.logout);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState('');
  const navigate = useNavigate();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [model, setModel] = useState('auto');
  const [piiCount, setPiiCount] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  async function send(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const text = input.trim();
    if (!text || pending) return;
    setError(null);
    setPiiCount(0);

    const slashHandled = handleSlash(text);
    if (slashHandled) {
      setInput('');
      return;
    }

    setInput('');

    const next: UiMessage[] = [
      ...messages,
      { role: 'user', content: text },
      { role: 'assistant', content: '', streaming: true },
    ];
    setMessages(next);
    setPending(true);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    const apiMessages: ChatMessage[] = next
      .filter((m) => !m.streaming)
      .map(({ role, content }) => ({ role, content }));

    try {
      for await (const event of streamChat({ messages: apiMessages, model, signal: ctrl.signal })) {
        if (event.type === 'token') {
          setMessages((cur) => {
            const copy = [...cur];
            const last = copy[copy.length - 1];
            if (last && last.role === 'assistant') {
              copy[copy.length - 1] = { ...last, content: last.content + event.text };
            }
            return copy;
          });
        } else if (event.type === 'pii_redacted') {
          setPiiCount(event.redactions.reduce((sum, item) => sum + item.count, 0));
        } else if (event.type === 'error') {
          setError(event.detail ?? event.error);
          break;
        } else if (event.type === 'done') {
          break;
        }
      }
    } catch (err) {
      if (!ctrl.signal.aborted) {
        setError(err instanceof Error ? err.message : 'stream failed');
      }
    } finally {
      setMessages((cur) => {
        const copy = [...cur];
        const last = copy[copy.length - 1];
        if (last && last.role === 'assistant' && last.streaming) {
          copy[copy.length - 1] = { ...last, streaming: false };
        }
        return copy;
      });
      setPending(false);
      abortRef.current = null;
    }
  }

  function addSystemMessage(content: string) {
    setMessages((cur) => [...cur, { role: 'assistant', content }]);
  }

  function handleSlash(text: string): boolean {
    const parsed = parseSlashCommand(text);
    if (!parsed) return false;
    if (parsed.command === 'model') {
      const nextModel = parsed.args[0];
      if (!nextModel) {
        addSystemMessage('Usage: /model <model_id> [--temp 0.7]');
        return true;
      }
      setModel(nextModel);
      addSystemMessage(`Model switched to ${nextModel}`);
      return true;
    }
    if (parsed.command === 'usage') {
      addSystemMessage('Usage analytics arrive in Phase 17. Current usage: unavailable.');
      return true;
    }
    if (parsed.command === 'help') {
      addSystemMessage(COMMANDS.map((cmd) => `/${cmd.name}${cmd.args ? ` ${cmd.args}` : ''} — ${cmd.description}`).join('\n'));
      return true;
    }
    if (parsed.command === 'skills') {
      void navigate({ to: '/skills' });
      return true;
    }
    if (parsed.command === 'memory') {
      void navigate({ to: '/memory' });
      return true;
    }
    if (parsed.command === 'tools') {
      void navigate({ to: '/mcp' });
      return true;
    }
    addSystemMessage(`/${parsed.command} is registered. Full execution is planned in a later phase.`);
    return true;
  }

  function pickSlash(cmd: SlashCommand) {
    setInput(`/${cmd.name}${cmd.args ? ' ' : ''}`);
  }

  function cancel() {
    abortRef.current?.abort();
  }

  return (
    <section className="max-w-2xl mx-auto flex flex-col gap-4 min-h-[70vh]">
      <header className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3"><h2 className="text-xl font-semibold">Chat</h2><ModelPicker value={model} onChange={setModel} profile="default" /></div>
          <div className="mt-1 flex items-center gap-2">
            <p className="text-xs text-black/60 dark:text-white/60">
              Signed in as <code>{user?.name ?? '—'}</code>
            </p>
            <PiiRedactedBadge count={piiCount} />
          </div>
        </div>
        <button
          onClick={() => void doLogout()}
          className="text-xs text-black/60 hover:text-black dark:text-white/60 dark:hover:text-white underline-offset-2 hover:underline"
        >
          Sign out
        </button>
      </header>

      <div className="flex-1 space-y-3 overflow-y-auto rounded-md border border-black/5 dark:border-white/10 p-4 bg-black/[0.02] dark:bg-white/[0.03]">
        {messages.length === 0 && (
          <p className="text-xs text-black/50 dark:text-white/50">
            Type a message below. SSE round-trip via the Phase 1 runtime adapter.
          </p>
        )}
        {messages.length > 500 ? (
          <Virtuoso
            style={{ height: '60vh' }}
            data={messages}
            itemContent={(i, message) => <Bubble key={i} message={message} />}
          />
        ) : (
          messages.map((m, i) => <Bubble key={i} message={m} />)
        )}
        {error && (
          <p className="text-xs text-rose-600 dark:text-rose-400" role="alert">
            {error}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <SlashMenu input={input} onPick={pickSlash} />
        <form onSubmit={send} className="flex items-end gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message…"
          rows={2}
          disabled={pending}
          className="flex-1 rounded-md border border-black/10 dark:border-white/15 bg-transparent px-3 py-2 text-sm outline-none resize-none focus:ring-2 focus:ring-sky-500/40"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              (e.currentTarget.form as HTMLFormElement | null)?.requestSubmit();
            }
          }}
        />
        {pending ? (
          <button
            type="button"
            onClick={cancel}
            className="rounded-md bg-rose-600 hover:bg-rose-700 text-white text-sm font-medium px-3 py-2"
          >
            Cancel
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim()}
            className="rounded-md bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white text-sm font-medium px-3 py-2"
          >
            Send
          </button>
        )}
        </form>
      </div>
    </section>
  );
}

function Bubble({ message }: { message: UiMessage }) {
  const isUser = message.role === 'user';
  return (
    <div className={isUser ? 'flex justify-end' : 'flex justify-start'}>
      <div
        className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap leading-relaxed ${
          isUser
            ? 'bg-sky-600 text-white rounded-br-md'
            : 'bg-black/5 dark:bg-white/10 rounded-bl-md'
        }`}
      >
        {message.content || (message.streaming ? '…' : '')}
      </div>
    </div>
  );
}
