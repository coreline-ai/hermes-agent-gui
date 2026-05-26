import { useIsMobile } from '@/hooks/use-mobile';

/**
 * Phase 9 — 3D feature flag (locked decision #5).
 * - ``VITE_FEATURE_3D=true`` + non-mobile → would lazy-load three.js avatar
 *   from an optional ``./avatar-3d`` companion package (not bundled by default).
 * - Otherwise → 2D fallback, always.
 *
 * The actual three.js component lives in a future opt-in package; until it
 * ships, this component always renders the 2D fallback so the bundle stays
 * lean. The branch is wired up so wiring is exercisable.
 */

interface Props {
  name?: string | undefined;
  size?: number;
}

const FLAG_ENABLED = (import.meta.env.VITE_FEATURE_3D === 'true') as boolean;

export function AgentAvatar(props: Props) {
  const isMobile = useIsMobile();
  // Always 2D until the optional ``./avatar-3d`` package ships.
  void FLAG_ENABLED;
  void isMobile;
  return <Avatar2D {...props} />;
}

export function Avatar2D({ name = 'Hermes', size = 36 }: Props) {
  const initial = name.charAt(0).toUpperCase();
  return (
    <div
      className="rounded-full flex items-center justify-center font-semibold text-white"
      style={{
        width: size,
        height: size,
        background: 'linear-gradient(135deg, #0ea5e9, #6366f1)',
        fontSize: size * 0.45,
      }}
      aria-label={`Avatar for ${name}`}
    >
      {initial}
    </div>
  );
}

export default AgentAvatar;
