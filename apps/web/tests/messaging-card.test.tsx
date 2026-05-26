import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PlatformCard } from '@/components/messaging/platform-card';
import type { PlatformMeta } from '@/lib/api';

function platform(id: string, mode: 'direct' | 'delegated'): PlatformMeta {
  return {
    id,
    label: id,
    mode,
    description: `${id} help`,
    credential_fields: [],
    behavior_schema: {},
    docs_url: 'https://example.test',
    requires_hermes_running: mode === 'delegated',
    configured: mode === 'direct',
    connected: false,
    last_event_at: null,
    last_error: null,
    behavior: {},
  };
}

describe('PlatformCard', () => {
  it('renders delegated and direct mode badges with accessible button names', () => {
    render(
      <div>
        <PlatformCard platform={platform('telegram', 'delegated')} onSelect={() => undefined} />
        <PlatformCard platform={platform('webhook', 'direct')} onSelect={() => undefined} />
      </div>,
    );

    expect(screen.getByRole('button', { name: /Open Telegram settings/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /Open Webhook settings/i })).toBeTruthy();
    expect(screen.getByText('Delegated')).toBeTruthy();
    expect(screen.getByText('Direct')).toBeTruthy();
  });
});
