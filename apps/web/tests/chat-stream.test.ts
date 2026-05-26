import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { streamChat, type ChatEvent } from '@/lib/chat-stream';

function makeSseStream(frames: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const f of frames) controller.enqueue(enc.encode(f));
      controller.close();
    },
  });
}

describe('streamChat', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(
          makeSseStream([
            'event: token\ndata: {"text":"hello "}\n\n',
            'event: token\ndata: {"text":"world"}\n\n',
            'event: done\ndata: {"session_id":"s1","adapter":"echo"}\n\n',
          ]),
          { status: 200, headers: { 'content-type': 'text/event-stream' } },
        ),
      ),
    );
  });

  afterEach(() => vi.unstubAllGlobals());

  it('parses token + done frames', async () => {
    const events: ChatEvent[] = [];
    for await (const e of streamChat({ messages: [{ role: 'user', content: 'hi' }] })) {
      events.push(e);
    }
    expect(events).toEqual([
      { type: 'token', text: 'hello ' },
      { type: 'token', text: 'world' },
      { type: 'done', session_id: 's1', turn_id: undefined, adapter: 'echo' },
    ]);
  });

  it('surfaces error events with detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(
          makeSseStream([
            'event: error\ndata: {"error":"backend_down","detail":"connect refused"}\n\n',
          ]),
          { status: 200, headers: { 'content-type': 'text/event-stream' } },
        ),
      ),
    );
    const events: ChatEvent[] = [];
    for await (const e of streamChat({ messages: [{ role: 'user', content: 'x' }] })) {
      events.push(e);
    }
    expect(events).toEqual([
      { type: 'error', error: 'backend_down', detail: 'connect refused' },
    ]);
  });

  it('throws when the response is not ok', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('boom', { status: 500 })));
    await expect(async () => {
      for await (const _ of streamChat({ messages: [{ role: 'user', content: 'x' }] })) {
        void _;
      }
    }).rejects.toThrow(/HTTP 500/);
  });
});
