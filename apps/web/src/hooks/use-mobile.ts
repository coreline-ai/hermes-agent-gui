import { useEffect, useState } from 'react';

/**
 * Phase 8 — adapted from A's `use-mobile-keyboard` + `mobile-page-header` cohort.
 * Watches a media query and stays in sync across orientation changes.
 */
export function useIsMobile(maxWidthPx = 768): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window === 'undefined' ? false : window.innerWidth <= maxWidthPx,
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const mql = window.matchMedia(`(max-width: ${maxWidthPx}px)`);
    const onChange = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener('change', onChange);
    setMatches(mql.matches);
    return () => mql.removeEventListener('change', onChange);
  }, [maxWidthPx]);

  return matches;
}
