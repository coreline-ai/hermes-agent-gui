import { Box, Text } from '@react-three/drei';

export function LibraryScene() {
  return (
    <group position={[0, 0, 1.5]}>
      <Box args={[3, 1.2, 0.2]} position={[0, 0.5, 0]}>
        <meshStandardMaterial color="#475569" />
      </Box>
      <Text position={[0, 1.25, -0.15]} fontSize={0.14} color="#e2e8f0">Memory Library</Text>
    </group>
  );
}
