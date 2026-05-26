import { Sphere, Text } from '@react-three/drei';

export function AgentAvatar3D() {
  return (
    <group position={[0, 0.55, 0.35]}>
      <Sphere args={[0.28, 32, 32]}>
        <meshStandardMaterial color="#8b5cf6" />
      </Sphere>
      <Text position={[0, 0.48, 0]} fontSize={0.12} color="#f8fafc">Hermes</Text>
    </group>
  );
}
