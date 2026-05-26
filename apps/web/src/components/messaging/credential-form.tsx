import type { CredentialField, PlatformMeta } from '@/lib/api';
import { useT } from '@/lib/i18n';
import { QrCodeFlow } from './qr-code-flow';

export function initialCredentials(platform: PlatformMeta): Record<string, string> {
  return Object.fromEntries(platform.credential_fields.map((field) => [field.name, '']));
}

export function CredentialForm({ platform, value, onChange }: { platform: PlatformMeta; value: Record<string, string>; onChange: (next: Record<string, string>) => void }) {
  const t = useT();
  if (platform.credential_fields.length === 0) {
    return <p className="text-xs text-black/60 dark:text-white/60">{t('messaging.credentials.none')}</p>;
  }

  function setField(field: CredentialField, next: string) {
    onChange({ ...value, [field.name]: next });
  }

  return (
    <fieldset className="space-y-3 rounded-lg border border-black/5 dark:border-white/10 p-3">
      <legend className="px-1 text-xs font-semibold">{t('messaging.credentials.title')}</legend>
      {platform.credential_fields.map((field) => {
        if (field.type === 'qr') {
          return (
            <div key={field.name}>
              <QrCodeFlow hint={field.placeholder} />
              <input type="hidden" value={value[field.name] ?? ''} readOnly />
            </div>
          );
        }
        if (field.type === 'select') {
          return (
            <label key={field.name} className="block text-xs">
              <span className="mb-1 block font-medium">{field.label}{field.required ? ' *' : ''}</span>
              <select
                aria-label={field.label}
                value={value[field.name] ?? ''}
                required={field.required}
                onChange={(e) => setField(field, e.target.value)}
                className="w-full rounded-md border border-black/10 dark:border-white/15 bg-transparent px-2 py-1.5 outline-none focus:ring-2 focus:ring-sky-500/40"
              >
                <option value="">{t('messaging.credentials.select')}</option>
                {(field.options ?? []).map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            </label>
          );
        }
        const type = field.type === 'password' ? 'password' : field.type === 'url' ? 'url' : 'text';
        return (
          <label key={field.name} className="block text-xs">
            <span className="mb-1 block font-medium">{field.label}{field.required ? ' *' : ''}</span>
            <input
              aria-label={field.label}
              type={type}
              value={value[field.name] ?? ''}
              required={field.required}
              pattern={field.pattern ?? undefined}
              placeholder={field.placeholder}
              onChange={(e) => setField(field, e.target.value)}
              className="w-full rounded-md border border-black/10 dark:border-white/15 bg-transparent px-2 py-1.5 outline-none focus:ring-2 focus:ring-sky-500/40"
            />
          </label>
        );
      })}
    </fieldset>
  );
}
