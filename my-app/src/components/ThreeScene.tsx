import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Stars, Text, MeshDistortMaterial, PerspectiveCamera } from '@react-three/drei';
import { useRef, useMemo } from 'react';
import * as THREE from 'three';

function ConnectionLines({ count = 50 }) {
  const lines = useMemo(() => {
    const temp = [];
    for (let i = 0; i < count; i++) {
        const start = new THREE.Vector3(
          (Math.random() - 0.5) * 20,
          (Math.random() - 0.5) * 20,
          (Math.random() - 0.5) * 20
        );
        const end = new THREE.Vector3(
          (Math.random() - 0.5) * 20,
          (Math.random() - 0.5) * 20,
          (Math.random() - 0.5) * 20
        );
        temp.push({ start, end });
    }
    return temp;
  }, [count]);

  return (
    <group>
      {lines.map((line, i) => (
        <line key={i}>
          <bufferGeometry attach="geometry" onUpdate={self => self.setFromPoints([line.start, line.end])} />
          <lineBasicMaterial attach="material" color="#c5a059" transparent opacity={0.05} />
        </line>
      ))}
    </group>
  );
}

function FloatingNodes({ count = 20 }) {
  const meshRef = useRef<THREE.Group>(null);
  
  useFrame((state) => {
    if (meshRef.current) {
        meshRef.current.rotation.y += 0.0008;
        meshRef.current.rotation.x += 0.0004;
    }
  });

  const nodes = useMemo(() => {
    const temp = [];
    for (let i = 0; i < count; i++) {
      temp.push({
        position: [
          (Math.random() - 0.5) * 15,
          (Math.random() - 0.5) * 15,
          (Math.random() - 0.5) * 15
        ],
        size: Math.random() * 0.3 + 0.05
      });
    }
    return temp;
  }, [count]);

  return (
    <group ref={meshRef}>
      {nodes.map((node, i) => (
        <mesh key={i} position={node.position as any}>
          <sphereGeometry args={[node.size, 16, 16]} />
          <meshStandardMaterial color="#c5a059" emissive="#c5a059" emissiveIntensity={1} />
        </mesh>
      ))}
    </group>
  );
}

export default function ThreeScene() {
  return (
    <div className="fixed inset-0 -z-10 bg-[#080808]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_#121212_0%,_#080808_100%)] opacity-80" />
      <Canvas>
        <PerspectiveCamera makeDefault position={[0, 0, 10]} />
        <ambientLight intensity={0.4} />
        <pointLight position={[10, 10, 10]} intensity={0.8} />
        
        <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
        
        <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
          <FloatingNodes />
          <ConnectionLines />
        </Float>

        <mesh position={[0, 0, -5]}>
          <sphereGeometry args={[10, 64, 64]} />
          <MeshDistortMaterial
            color="#111"
            speed={2}
            distort={0.4}
            radius={1}
          />
        </mesh>
      </Canvas>
    </div>
  );
}
