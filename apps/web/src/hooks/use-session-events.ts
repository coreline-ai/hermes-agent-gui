import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

/**
 * Subscribe to ``GET /api/sessions/_stream`` and invalidate the sessions query
 * on every server-side change. Uses the native ``EventSource`` (no auth header
 * needed — the HMAC cookie travels automatically).
 *
 * One subscriber per mount; auto-reconnects via EventSource's built-in
 * retry. The hook is a no-op outside the browser.
 */
export function useSessionEvents(): void {
  const qc = useQueryClient();
  useEffect(() => {
    if (typeof window === 'undefined' || typeof EventSource === 'undefined') return;
    const es = new EventSource('/api/sessions/_stream');

    const invalidate = () => {
      void qc.invalidateQueries({ queryKey: ['sessions'] });
      void qc.invalidateQueries({ queryKey: ['dashboard'] });
    };

    es.addEventListener('session_list_changed', invalidate);
    es.addEventListener('session_updated', invalidate);
    es.addEventListener('session_deleted', invalidate);
    es.addEventListener('error', () => {
      // EventSource auto-reconnects with backoff; this listener just silences
      // the console noise during dev when the server restarts.
    });

    return () => es.close();
  }, [qc]);
}
