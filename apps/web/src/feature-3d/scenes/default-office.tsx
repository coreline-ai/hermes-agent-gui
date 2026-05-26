import { Box, Text } from '@react-three/drei';

export function DefaultOfficeScene() {
  return (
    <group>
      <Box args={[4, 0.2, 2]} position={[0, -0.1, 0]}>
        <meshStandardMaterial color="#334155" />
      </Box>
      <Box args={[1.6, 0.12, 0.8]} position={[-0.9, 0.25, 0]}>
        <meshStandardMaterial color="#b45309" />
      </Box>
      <Box args={[1.4, 0.8, 0.08]} position={[1.1, 0.55, -0.75]}>
        <meshStandardMaterial color="#0ea5e9" />
      </Box>
      <Text position={[1.1, 0.58, -0.81]} fontSize={0.12} color="white">Kanban</Text>
    </group>
  );
}
