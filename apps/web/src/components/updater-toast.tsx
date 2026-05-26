import { useEffect, useState } from 'react';

declare global {
  interface Window {
    hermesElectron?: {
      version?: string;
      platform?: string;
      downloadUpdate?: () => Promise<unknown>;
      onUpdateAvailable?: (cb: (info: { version?: string }) => void) => void;
    };
  }
}

export function UpdaterToast() {
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    window.hermesElectron?.onUpdateAvailable?.((info) => setVersion(info.version ?? 'new'));
  }, []);

  if (!version) return null;
  return (
    <div className="fixed bottom-4 right-4 z-50 w-72 rounded-xl border border-sky-500/30 bg-white p-4 text-sm shadow-xl dark:bg-slate-950">
      <p className="font-semibold">Hermes GUI {version} 사용 가능</p>
      <p className="mt-1 text-xs text-black/60 dark:text-white/60">Electron auto-updater가 새 릴리스를 감지했습니다.</p>
      <div className="mt-3 flex justify-end gap-2">
        <button onClick={() => setVersion(null)} className="rounded-md px-3 py-1 text-xs hover:bg-black/5 dark:hover:bg-white/10">Later</button>
        <button onClick={() => void window.hermesElectron?.downloadUpdate?.()} className="rounded-md bg-sky-600 px-3 py-1 text-xs font-medium text-white hover:bg-sky-700">Download</button>
      </div>
    </div>
  );
}
