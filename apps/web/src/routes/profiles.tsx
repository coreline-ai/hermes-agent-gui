import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { type DragEvent, useRef, useState } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card, ErrorMsg } from '@/components/page';
import { ApiError, Profiles, type ProfileInfo } from '@/lib/api';
import { useT } from '@/lib/i18n';
import { useAuthStore } from '@/stores/auth-store';

export const Route = createFileRoute('/profiles')({
  beforeLoad: requireAuth,
  component: ProfilesPage,
});

function errorText(error: unknown): string {
  if (error instanceof ApiError && error.payload && typeof error.payload === 'object') {
    const payload = error.payload as Record<string, unknown>;
    return String(payload.detail ?? payload.error ?? error.message);
  }
  return error instanceof Error ? error.message : String(error);
}

function ProfilesPage() {
  const t = useT();
  const qc = useQueryClient();
  const logout = useAuthStore((s) => s.logout);
  const list = useQuery({ queryKey: ['profiles'], queryFn: Profiles.list });
  const [cloneSource, setCloneSource] = useState('default');
  const [cloneName, setCloneName] = useState('');
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const profiles = list.data?.profiles ?? [];

  const cloneMut = useMutation({
    mutationFn: () => Profiles.clone(cloneSource, cloneName),
    onSuccess: (result) => {
      setCloneName('');
      setToast(t('profiles.clone.ok', { name: result.name }));
      setError(null);
      void qc.invalidateQueries({ queryKey: ['profiles'] });
    },
    onError: (err) => setError(errorText(err)),
  });

  const importMut = useMutation({
    mutationFn: (file: File) => Profiles.importArchive(file),
    onSuccess: async (result) => {
      setError(null);
      setToast(t('profiles.import.relogin', { name: result.imported_profile }));
      void qc.invalidateQueries({ queryKey: ['profiles'] });
      window.setTimeout(() => {
        void logout();
      }, 900);
    },
    onError: (err) => setError(errorText(err)),
  });

  async function exportProfile(profile: ProfileInfo) {
    setError(null);
    try {
      const res = await fetch(Profiles.exportUrl(profile.name), {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new ApiError(res.status, await res.json().catch(() => null));
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `hermes-profile-${profile.name}.tar.gz`;
      a.click();
      window.URL.revokeObjectURL(url);
      setToast(t('profiles.export.ok', { name: profile.name }));
    } catch (err) {
      setError(errorText(err));
    }
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    const file = e.dataTransfer.files.item(0);
    if (file) importMut.mutate(file);
  }

  return (
    <Page title={t('profiles.title')} action={<span className="text-xs text-black/55 dark:text-white/55">{t('profiles.subtitle')}</span>}>
      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <Card>
          {list.isPending && <p className="text-xs">{t('common.loading')}</p>}
          <ul className="divide-y divide-black/5 dark:divide-white/10 -m-4">
            {profiles.map((profile) => (
              <li key={profile.name} className="flex items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{profile.name}</p>
                  <p className="text-[10px] text-black/55 dark:text-white/55">
                    {t('profiles.sessionCount', { count: profile.session_count })}
                    {profile.has_profile_dir ? ` · ${t('profiles.hasProfileDir')}` : ''}
                    {profile.updated_at ? ` · ${new Date(profile.updated_at * 1000).toLocaleString()}` : ''}
                  </p>
                </div>
                <button
                  type="button"
                  aria-label={t('profiles.exportFor', { name: profile.name })}
                  onClick={() => void exportProfile(profile)}
                  className="rounded-md border border-black/10 px-3 py-1.5 text-xs hover:bg-black/5 dark:border-white/15 dark:hover:bg-white/10"
                >
                  {t('profiles.export')}
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <aside className="space-y-4">
          <Card>
            <h3 className="mb-3 text-sm font-semibold">{t('profiles.clone.title')}</h3>
            <form
              className="space-y-3"
              onSubmit={(e) => {
                e.preventDefault();
                cloneMut.mutate();
              }}
            >
              <label className="block text-xs">
                <span className="mb-1 block font-medium">{t('profiles.clone.source')}</span>
                <select
                  aria-label={t('profiles.clone.source')}
                  value={cloneSource}
                  onChange={(e) => setCloneSource(e.target.value)}
                  className="w-full rounded-md border border-black/10 bg-transparent px-2 py-1.5 dark:border-white/15"
                >
                  {profiles.map((profile) => (
                    <option key={profile.name} value={profile.name}>{profile.name}</option>
                  ))}
                </select>
              </label>
              <label className="block text-xs">
                <span className="mb-1 block font-medium">{t('profiles.clone.newName')}</span>
                <input
                  aria-label={t('profiles.clone.newName')}
                  value={cloneName}
                  required
                  onChange={(e) => setCloneName(e.target.value)}
                  className="w-full rounded-md border border-black/10 bg-transparent px-2 py-1.5 outline-none focus:ring-2 focus:ring-sky-500/40 dark:border-white/15"
                />
              </label>
              <button
                type="submit"
                disabled={cloneMut.isPending || !cloneName.trim()}
                className="rounded-md bg-sky-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-700 disabled:opacity-50"
              >
                {t('profiles.clone.action')}
              </button>
            </form>
          </Card>

          <Card>
            <h3 className="mb-3 text-sm font-semibold">{t('profiles.import.title')}</h3>
            <div
              role="button"
              tabIndex={0}
              aria-label={t('profiles.import.dropzone')}
              onDrop={onDrop}
              onDragOver={(e) => e.preventDefault()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click();
              }}
              onClick={() => inputRef.current?.click()}
              className="cursor-pointer rounded-lg border border-dashed border-black/20 p-5 text-center text-xs text-black/60 outline-none hover:bg-black/5 focus:ring-2 focus:ring-sky-500/40 dark:border-white/20 dark:text-white/60 dark:hover:bg-white/10"
            >
              {importMut.isPending ? t('profiles.import.running') : t('profiles.import.dropzone')}
            </div>
            <input
              ref={inputRef}
              type="file"
              accept=".tar.gz,application/gzip,application/x-gzip"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.item(0);
                if (file) importMut.mutate(file);
                e.currentTarget.value = '';
              }}
            />
          </Card>
        </aside>
      </div>
      {toast && <p className="text-xs text-emerald-700 dark:text-emerald-300" role="status">{toast}</p>}
      <ErrorMsg>{error}</ErrorMsg>
    </Page>
  );
}
