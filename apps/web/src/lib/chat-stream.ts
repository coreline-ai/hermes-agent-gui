export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface TokenEvent {
  type: 'token';
  text: string;
}

export interface DoneEvent {
  type: 'done';
  session_id?: string;
  turn_id?: string;
  adapter?: string;
}

export interface PiiRedactedEvent {
  type: 'pii_redacted';
  redactions: { kind: string; count: number }[];
}

export interface ErrorEvent {
  type: 'error';
  error: string;
  detail?: string;
}

export type ChatEvent = TokenEvent | DoneEvent | ErrorEvent | PiiRedactedEvent;

interface StreamOptions {
  messages: ChatMessage[];
  sessionId?: string | undefined;
  model?: string | undefined;
  providerId?: string | undefined;
  profile?: string | undefined;
  title?: string | undefined;
  autoCreateSession?: boolean | undefined;
  signal?: AbortSignal | undefined;
}

/** POST /api/chat/stream and yield decoded SSE events. */
export async function* streamChat(opts: StreamOptions): AsyncGenerator<ChatEvent, void, void> {
  const res = await fetch('/api/chat/stream', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: opts.messages,
      session_id: opts.sessionId,
      model: opts.model,
      provider_id: opts.providerId,
      profile: opts.profile,
      title: opts.title,
      auto_create_session: opts.autoCreateSession,
    }),
    signal: opts.signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`chat stream failed: HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buf = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });

      let sep: number;
      while ((sep = buf.indexOf('\n\n')) !== -1) {
        const frame = buf.slice(0, sep);
        buf = buf.slice(sep + 2);
        const parsed = parseFrame(frame);
        if (parsed) yield parsed;
      }
    }
    // Drain any trailing frame.
    if (buf.trim()) {
      const parsed = parseFrame(buf);
      if (parsed) yield parsed;
    }
  } finally {
    reader.releaseLock();
  }
}

function parseFrame(frame: string): ChatEvent | null {
  let event = 'message';
  const dataLines: string[] = [];
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim());
    }
  }
  if (dataLines.length === 0) return null;
  const dataStr = dataLines.join('\n');
  let payload: Record<string, unknown> = {};
  try {
    payload = JSON.parse(dataStr) as Record<string, unknown>;
  } catch {
    return null;
  }

  if (event === 'token') {
    return { type: 'token', text: String(payload.text ?? '') };
  }
  if (event === 'done') {
    return {
      type: 'done',
      session_id: payload.session_id as string | undefined,
      turn_id: payload.turn_id as string | undefined,
      adapter: payload.adapter as string | undefined,
    };
  }
  if (event === 'pii_redacted') {
    const redactions = Array.isArray(payload.redactions)
      ? (payload.redactions as { kind: string; count: number }[])
      : [];
    return { type: 'pii_redacted', redactions };
  }
  if (event === 'error') {
    return {
      type: 'error',
      error: String(payload.error ?? 'unknown_error'),
      detail: payload.detail as string | undefined,
    };
  }
  return null;
}
