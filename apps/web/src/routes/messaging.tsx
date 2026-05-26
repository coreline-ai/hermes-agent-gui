import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { BehaviorEditor, defaultBehavior } from '@/components/messaging/behavior-editor';
import { CredentialForm, initialCredentials } from '@/components/messaging/credential-form';
import { PlatformCard } from '@/components/messaging/platform-card';
import { StatusBadge } from '@/components/messaging/status-badge';
import { ApiError, Messaging, type PlatformMeta, type WebhookConfigureResponse } from '@/lib/api';
import { useT } from '@/lib/i18n';

export const Route = createFileRoute('/messaging')({
  beforeLoad: requireAuth,
  component: MessagingPage,
});

function errorText(error: unknown): string {
  if (error instanceof ApiError && error.payload && typeof error.payload === 'object') {
    const payload = error.payload as Record<string, unknown>;
    return String(payload.detail ?? payload.error ?? error.message);
  }
  return error instanceof Error ? error.message : String(error);
}

function MessagingPage() {
  const t = useT();
  const query = useQuery({ queryKey: ['messaging-platforms'], queryFn: Messaging.platforms });
  const platforms = useMemo(() => query.data?.platforms ?? [], [query.data?.platforms]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = useMemo(
    () => platforms.find((platform) => platform.id === selectedId) ?? platforms[0] ?? null,
    [platforms, selectedId],
  );

  useEffect(() => {
    if (!selectedId && platforms.length > 0) setSelectedId(platforms[0]?.id ?? null);
  }, [platforms, selectedId]);

  return (
    <Page title={t('messaging.title')} action={<span className="text-xs text-black/55 dark:text-white/55">{t('messaging.subtitle')}</span>}>
      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <section aria-label={t('messaging.grid.label')} className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {query.isPending && <Card>{t('common.loading')}</Card>}
          {platforms.map((platform) => (
            <PlatformCard
              key={platform.id}
              platform={platform}
              selected={selected?.id === platform.id}
              onSelect={() => setSelectedId(platform.id)}
            />
          ))}
        </section>
        <aside aria-label={t('messaging.drawer.label')} className="lg:sticky lg:top-4 lg:self-start">
          {selected ? <PlatformDrawer platform={selected} /> : <Card>{t('messaging.empty')}</Card>}
        </aside>
      </div>
    </Page>
  );
}

function PlatformDrawer({ platform }: { platform: PlatformMeta }) {
  const t = useT();
  const qc = useQueryClient();
  const [credentials, setCredentials] = useState<Record<string, string>>(() => initialCredentials(platform));
  const [behavior, setBehavior] = useState<Record<string, unknown>>(() => defaultBehavior(platform));
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [webhook, setWebhook] = useState<WebhookConfigureResponse | null>(null);

  useEffect(() => {
    setCredentials(initialCredentials(platform));
    setBehavior(defaultBehavior(platform));
    setMessage(null);
    setError(null);
    setWebhook(null);
  }, [platform]);

  const configureMut = useMutation({
    mutationFn: () => Messaging.configure(platform.id, { credentials, behavior }),
    onSuccess: (result) => {
      setError(null);
      setMessage(t('messaging.saved'));
      if ('token' in result) setWebhook(result);
      void qc.invalidateQueries({ queryKey: ['messaging-platforms'] });
    },
    onError: (err) => setError(errorText(err)),
  });

  const rotateWebhookMut = useMutation({
    mutationFn: () => Messaging.configure(platform.id, { credentials: {}, behavior, rotate: true }),
    onSuccess: (result) => {
      setError(null);
      setMessage(t('messaging.webhook.rotated'));
      if ('token' in result) setWebhook(result);
      void qc.invalidateQueries({ queryKey: ['messaging-platforms'] });
    },
    onError: (err) => setError(errorText(err)),
  });

  const testMut = useMutation({
    mutationFn: () => Messaging.test(platform.id),
    onSuccess: (result) => {
      setError(null);
      setMessage(`${t('messaging.test.ok')}: ${JSON.stringify(result)}`);
      void qc.invalidateQueries({ queryKey: ['messaging-platforms'] });
    },
    onError: (err) => setError(errorText(err)),
  });

  const disableMut = useMutation({
    mutationFn: () => Messaging.disable(platform.id),
    onSuccess: () => {
      setError(null);
      setMessage(t('messaging.disabled'));
      void qc.invalidateQueries({ queryKey: ['messaging-platforms'] });
    },
    onError: (err) => setError(errorText(err)),
  });

  const label = t(`messaging.platform.${platform.id}.label`);
  const help = t(`messaging.platform.${platform.id}.help`);

  return (
    <Card className="space-y-4">
      <header className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold">{label}</h3>
            <p className="mt-1 text-xs leading-5 text-black/60 dark:text-white/60">{help}</p>
          </div>
          <StatusBadge configured={platform.configured} connected={platform.connected} lastError={platform.last_error} />
        </div>
        <div className="flex flex-wrap gap-2 text-[10px]">
          <span className="rounded-full bg-black/5 px-2 py-0.5 dark:bg-white/10">
            {platform.mode === 'direct' ? t('messaging.mode.direct') : t('messaging.mode.delegated')}
          </span>
          {platform.requires_hermes_running && <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-amber-700 dark:text-amber-300">{t('messaging.requiresHermes')}</span>}
        </div>
      </header>

      <CredentialForm platform={platform} value={credentials} onChange={setCredentials} />
      <BehaviorEditor platform={platform} value={behavior} onChange={setBehavior} />

      {webhook && (
        <div className="rounded-lg border border-sky-500/20 bg-sky-500/10 p-3 text-xs">
          <p className="font-semibold">{t('messaging.webhook.secretUrl')}</p>
          <code className="mt-2 block break-all rounded bg-black/5 p-2 dark:bg-white/10">{webhook.url}</code>
          <p className="mt-2 text-black/60 dark:text-white/60">{t('messaging.webhook.secretHelp')}</p>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          aria-label={t('messaging.action.saveFor', { platform: label })}
          disabled={configureMut.isPending}
          onClick={() => configureMut.mutate()}
          className="rounded-md bg-sky-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-700 disabled:opacity-50"
        >
          {t('common.save')}
        </button>
        {platform.id === 'webhook' && (
          <button
            type="button"
            aria-label={t('messaging.webhook.rotate')}
            disabled={rotateWebhookMut.isPending}
            onClick={() => rotateWebhookMut.mutate()}
            className="rounded-md border border-black/10 px-3 py-1.5 text-xs hover:bg-black/5 disabled:opacity-50 dark:border-white/15 dark:hover:bg-white/10"
          >
            {t('messaging.webhook.rotate')}
          </button>
        )}
        <button
          type="button"
          aria-label={t('messaging.action.testFor', { platform: label })}
          disabled={testMut.isPending}
          onClick={() => testMut.mutate()}
          className="rounded-md border border-black/10 px-3 py-1.5 text-xs hover:bg-black/5 disabled:opacity-50 dark:border-white/15 dark:hover:bg-white/10"
        >
          {t('messaging.action.test')}
        </button>
        <button
          type="button"
          aria-label={t('messaging.action.disableFor', { platform: label })}
          disabled={disableMut.isPending}
          onClick={() => disableMut.mutate()}
          className="rounded-md border border-rose-500/30 px-3 py-1.5 text-xs text-rose-600 hover:bg-rose-500/10 disabled:opacity-50 dark:text-rose-300"
        >
          {t('messaging.action.disable')}
        </button>
      </div>

      {message && <p className="text-xs text-emerald-700 dark:text-emerald-300" role="status">{message}</p>}
      <ErrorMsg>{error}</ErrorMsg>
    </Card>
  );
}
