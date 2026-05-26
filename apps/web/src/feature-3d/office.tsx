import { Canvas } from '@react-three/fiber';
import { Environment, OrbitControls } from '@react-three/drei';
import { AgentAvatar3D } from './characters/agent-avatar-3d';
import { DefaultOfficeScene } from './scenes/default-office';
import { LibraryScene } from './scenes/library';

export function Office3D() {
  return (
    <div className="h-[70vh] overflow-hidden rounded-xl border border-black/5 bg-slate-950 dark:border-white/10">
      <Canvas camera={{ position: [3, 2.4, 4], fov: 45 }}>
        <ambientLight intensity={0.7} />
        <directionalLight position={[3, 5, 3]} intensity={1.4} />
        <DefaultOfficeScene />
        <LibraryScene />
        <AgentAvatar3D />
        <OrbitControls makeDefault />
        <Environment preset="city" />
      </Canvas>
    </div>
  );
}
