import { createFileRoute, Link } from '@tanstack/react-router';
import { lazy, Suspense } from 'react';
import { requireAuth } from '@/components/auth-guard';
import { Page, Card } from '@/components/page';
import { useIsMobile } from '@/hooks/use-mobile';

export const Route = createFileRoute('/office')({
  beforeLoad: requireAuth,
  component: OfficePage,
});

const LazyOffice = lazy(() => import('@/feature-3d/office').then((module) => ({ default: module.Office3D })));

function OfficePage() {
  const mobile = useIsMobile();
  const enabled = import.meta.env.VITE_FEATURE_3D === 'true' && !mobile;
  return (
    <Page title="Hermes Office" action={<span className="text-xs text-black/55 dark:text-white/55">Feature flag: VITE_FEATURE_3D</span>}>
      {enabled ? (
        <Suspense fallback={<Card>Loading 3D office…</Card>}><LazyOffice /></Suspense>
      ) : (
        <Card>
          <h3 className="text-lg font-semibold">2D fallback workspace</h3>
          <p className="mt-2 text-sm text-black/60 dark:text-white/60">3D office is lazy-loaded only when the feature flag is enabled on desktop.</p>
          <div className="mt-4 flex gap-2 text-xs"><Link to="/tasks" className="underline">Tasks</Link><Link to="/chat" className="underline">Chat</Link><Link to="/brain" className="underline">Brain</Link></div>
        </Card>
      )}
    </Page>
  );
}
