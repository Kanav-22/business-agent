"use client";

import {
  createRoot,
  extend,
  useFrame,
  type ReconcilerRoot,
} from "@react-three/fiber";
import {
  Component,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MutableRefObject,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import * as THREE from "three";

import { AGENT_NODES, CEO_NODE, type ConstellationNode } from "./constellation-data";
import { StaticHeroFallback } from "./static-hero-fallback";

const MAX_TILT = THREE.MathUtils.degToRad(6);
const PARTICLE_COUNT = 220;
const LINE_SEGMENTS = 28;

// Canvas registers the complete THREE namespace. This scene uses a deliberately
// small R3F catalogue so the lazy bundle only carries objects we actually render.
extend({
  AmbientLight: THREE.AmbientLight,
  DirectionalLight: THREE.DirectionalLight,
  Group: THREE.Group,
  Mesh: THREE.Mesh,
  MeshBasicMaterial: THREE.MeshBasicMaterial,
  MeshStandardMaterial: THREE.MeshStandardMaterial,
  PointLight: THREE.PointLight,
  RingGeometry: THREE.RingGeometry,
  SphereGeometry: THREE.SphereGeometry,
  Sprite: THREE.Sprite,
  SpriteMaterial: THREE.SpriteMaterial,
});

const CAMERA = { fov: 42, near: 0.1, far: 40 };
const GL_OPTIONS = {
  alpha: true,
  antialias: true,
  powerPreference: "high-performance" as const,
};
const PERFORMANCE = { min: 0.5, max: 1, debounce: 200 };

type ParallaxTarget = { x: number; y: number };

export type HeroSceneProps = {
  className?: string;
  /** Increment this number to launch one ripple wave from the CEO node. */
  pulseSignal?: number;
};

type WebGLErrorBoundaryState = { failed: boolean };

class WebGLErrorBoundary extends Component<
  { children: ReactNode },
  WebGLErrorBoundaryState
> {
  state: WebGLErrorBoundaryState = { failed: false };

  static getDerivedStateFromError(): WebGLErrorBoundaryState {
    return { failed: true };
  }

  render() {
    if (this.state.failed) return <StaticHeroFallback reason="webgl-error" />;
    return this.props.children;
  }
}

function SceneCanvas({
  children,
  isVisible,
}: {
  children: ReactNode;
  isVisible: boolean;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const root = useRef<ReconcilerRoot<HTMLCanvasElement> | null>(null);
  const pendingUnmount = useRef<number | null>(null);
  const latestChildren = useRef(children);
  const latestVisibility = useRef(isVisible);
  const refresh = useRef<() => void>(() => undefined);

  latestChildren.current = children;
  latestVisibility.current = isVisible;

  useEffect(() => {
    const element = canvas.current;
    if (!element) return;

    if (pendingUnmount.current !== null) {
      window.clearTimeout(pendingUnmount.current);
      pendingUnmount.current = null;
    }

    const fiberRoot = root.current ?? createRoot(element);
    root.current ??= fiberRoot;

    const configureAndRender = () => {
      const bounds = element.getBoundingClientRect();
      if (bounds.width <= 0 || bounds.height <= 0) return;
      const aspect = bounds.width / bounds.height;
      const cameraDistance = aspect < 1 ? 9.2 / Math.max(aspect, 0.65) : 8.6;

      fiberRoot
        .configure({
          camera: {
            ...CAMERA,
            position: [0, 0, cameraDistance],
          },
          dpr: [1, 1.5],
          frameloop: latestVisibility.current ? "always" : "never",
          gl: GL_OPTIONS,
          performance: PERFORMANCE,
          size: {
            width: bounds.width,
            height: bounds.height,
            left: 0,
            top: 0,
            updateStyle: false,
          },
          onCreated: ({ gl }) => {
            gl.setClearColor(0x000000, 0);
            gl.outputColorSpace = THREE.SRGBColorSpace;
          },
        })
        .render(latestChildren.current);
    };

    refresh.current = configureAndRender;
    try {
      configureAndRender();
    } catch (error) {
      refresh.current = () => undefined;
      root.current = null;
      fiberRoot.unmount();
      throw error;
    }

    const observer =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(configureAndRender);

    if (observer) observer.observe(element);
    else window.addEventListener("resize", configureAndRender);

    return () => {
      refresh.current = () => undefined;
      observer?.disconnect();
      if (!observer) window.removeEventListener("resize", configureAndRender);
      // Defer disposal by one task so React Strict Mode's effect replay can
      // reuse the same R3F root instead of creating a duplicate root.
      pendingUnmount.current = window.setTimeout(() => {
        if (root.current === fiberRoot) {
          root.current = null;
          fiberRoot.unmount();
        }
        pendingUnmount.current = null;
      }, 0);
    };
  }, []);

  useEffect(() => {
    refresh.current();
  }, [children, isVisible]);

  return (
    <canvas
      ref={canvas}
      className="block h-full w-full"
      data-scene-frame-loop={isVisible ? "always" : "never"}
      style={{ pointerEvents: "none" }}
    />
  );
}

function useIsVisible(container: MutableRefObject<HTMLDivElement | null>) {
  const [isIntersecting, setIsIntersecting] = useState(true);
  const [documentVisible, setDocumentVisible] = useState(true);

  useEffect(() => {
    const element = container.current;
    if (!element || typeof IntersectionObserver === "undefined") return;

    const observer = new IntersectionObserver(
      ([entry]) => setIsIntersecting(entry.isIntersecting),
      { threshold: 0.01 },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [container]);

  useEffect(() => {
    const update = () => setDocumentVisible(document.visibilityState !== "hidden");
    update();
    document.addEventListener("visibilitychange", update);
    return () => document.removeEventListener("visibilitychange", update);
  }, []);

  return isIntersecting && documentVisible;
}

function nodeBob(elapsed: number, phase: number) {
  return Math.sin(elapsed * 0.62 + phase) * 0.085;
}

function createGlowTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 96;
  canvas.height = 96;
  const context = canvas.getContext("2d");

  if (!context) return new THREE.Texture();

  const gradient = context.createRadialGradient(48, 48, 0, 48, 48, 48);
  gradient.addColorStop(0, "rgba(255,255,255,0.92)");
  gradient.addColorStop(0.15, "rgba(255,255,255,0.46)");
  gradient.addColorStop(0.48, "rgba(255,255,255,0.1)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, 96, 96);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.needsUpdate = true;
  return texture;
}

function AgentNode({ node, glowTexture }: { node: ConstellationNode; glowTexture: THREE.Texture }) {
  const group = useRef<THREE.Group>(null);
  const glow = useRef<THREE.SpriteMaterial>(null);

  useFrame(({ clock }) => {
    if (!group.current) return;
    const elapsed = clock.getElapsedTime();
    group.current.position.y = node.position[1] + nodeBob(elapsed, node.phase);
    if (glow.current) {
      glow.current.opacity = 0.2 + Math.sin(elapsed * 0.7 + node.phase) * 0.035;
    }
  });

  return (
    <group
      ref={group}
      name={node.label}
      position={[node.position[0], node.position[1], node.position[2]]}
    >
      <sprite scale={[0.82, 0.82, 1]}>
        <spriteMaterial
          ref={glow}
          map={glowTexture}
          color={node.color}
          transparent
          opacity={0.2}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </sprite>
      <mesh>
        <sphereGeometry args={[0.145, 18, 18]} />
        <meshStandardMaterial
          color={node.color}
          emissive={node.color}
          emissiveIntensity={1.65}
          metalness={0.12}
          roughness={0.32}
        />
      </mesh>
      <mesh scale={1.42}>
        <sphereGeometry args={[0.145, 14, 14]} />
        <meshBasicMaterial
          color={node.color}
          transparent
          opacity={0.11}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

function CeoNode({ glowTexture }: { glowTexture: THREE.Texture }) {
  const group = useRef<THREE.Group>(null);
  const glow = useRef<THREE.SpriteMaterial>(null);

  useFrame(({ clock }) => {
    const elapsed = clock.getElapsedTime();
    const breath = 1 + Math.sin(elapsed * 0.82) * 0.025;
    group.current?.scale.setScalar(breath);
    if (glow.current) glow.current.opacity = 0.32 + Math.sin(elapsed * 0.7) * 0.045;
  });

  return (
    <group ref={group} name={CEO_NODE.label}>
      <sprite scale={[1.75, 1.75, 1]}>
        <spriteMaterial
          ref={glow}
          map={glowTexture}
          color={CEO_NODE.color}
          transparent
          opacity={0.32}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </sprite>
      <mesh>
        <sphereGeometry args={[0.32, 26, 26]} />
        <meshStandardMaterial
          color={CEO_NODE.color}
          emissive={CEO_NODE.color}
          emissiveIntensity={2.1}
          metalness={0.2}
          roughness={0.25}
        />
      </mesh>
      <mesh scale={1.24}>
        <sphereGeometry args={[0.32, 18, 18]} />
        <meshBasicMaterial
          color={CEO_NODE.color}
          transparent
          opacity={0.13}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
      <pointLight color={CEO_NODE.color} intensity={4.2} distance={4.5} decay={2} />
    </group>
  );
}

function DelegationLine({ node, index }: { node: ConstellationNode; index: number }) {
  const { geometry, material, line, positionAttribute } = useMemo(() => {
    const positions = new Float32Array((LINE_SEGMENTS + 1) * 3);
    const attribute = new THREE.BufferAttribute(positions, 3);
    attribute.setUsage(THREE.DynamicDrawUsage);

    const nextGeometry = new THREE.BufferGeometry();
    nextGeometry.setAttribute("position", attribute);
    const nextMaterial = new THREE.LineBasicMaterial({
      color: node.color,
      transparent: true,
      opacity: 0.275,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const nextLine = new THREE.Line(nextGeometry, nextMaterial);
    nextLine.frustumCulled = false;
    nextLine.renderOrder = 1;

    return {
      geometry: nextGeometry,
      material: nextMaterial,
      line: nextLine,
      positionAttribute: attribute,
    };
  }, [node.color]);

  useEffect(
    () => () => {
      geometry.dispose();
      material.dispose();
    },
    [geometry, material],
  );

  useFrame(({ clock }) => {
    const elapsed = clock.getElapsedTime();
    const endX = node.position[0];
    const endY = node.position[1] + nodeBob(elapsed, node.phase);
    const endZ = node.position[2];
    const controlX = endX * 0.48 + (index % 2 === 0 ? -0.18 : 0.18);
    const controlY = endY * 0.48 + 0.34;
    const controlZ = endZ * 0.48 + (index % 3 - 1) * 0.24;
    const positions = positionAttribute.array as Float32Array;

    for (let segment = 0; segment <= LINE_SEGMENTS; segment += 1) {
      const t = segment / LINE_SEGMENTS;
      const oneMinusT = 1 - t;
      const curve = 2 * oneMinusT * t;
      const endWeight = t * t;
      const offset = segment * 3;
      positions[offset] = curve * controlX + endWeight * endX;
      positions[offset + 1] = curve * controlY + endWeight * endY;
      positions[offset + 2] = curve * controlZ + endWeight * endZ;
    }

    positionAttribute.needsUpdate = true;
    material.opacity = 0.275 + Math.sin(elapsed * 0.86 + node.phase) * 0.125;
  });

  return <primitive object={line} />;
}

function ParticleField() {
  const points = useMemo(() => {
    let seed = 0x86c2a5d1;
    const random = () => {
      seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
      return seed / 4294967296;
    };

    const positions = new Float32Array(PARTICLE_COUNT * 3);
    for (let index = 0; index < PARTICLE_COUNT; index += 1) {
      const radius = 3.8 + random() * 3.4;
      const theta = random() * Math.PI * 2;
      const phi = Math.acos(2 * random() - 1);
      positions[index * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[index * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[index * 3 + 2] = radius * Math.cos(phi) - 1.2;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const material = new THREE.PointsMaterial({
      color: "#cbd5e1",
      size: 0.025,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.34,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const field = new THREE.Points(geometry, material);
    field.frustumCulled = false;
    field.renderOrder = 0;
    return field;
  }, []);

  useEffect(
    () => () => {
      points.geometry.dispose();
      (points.material as THREE.Material).dispose();
    },
    [points],
  );

  useFrame((_, delta) => {
    points.rotation.y += delta * 0.006;
    points.rotation.x += delta * 0.0015;
  });

  return <primitive object={points} />;
}

function RippleRing({
  pulseSignal,
  delay,
}: {
  pulseSignal: number;
  delay: number;
}) {
  const mesh = useRef<THREE.Mesh>(null);
  const material = useRef<THREE.MeshBasicMaterial>(null);
  const lastSignal = useRef(0);
  const startTime = useRef<number | null>(null);
  const active = useRef(false);

  useEffect(() => {
    if (pulseSignal <= 0 || pulseSignal === lastSignal.current) return;
    lastSignal.current = pulseSignal;
    startTime.current = null;
    active.current = true;
  }, [pulseSignal]);

  useFrame(({ clock }) => {
    if (!mesh.current || !material.current || !active.current) return;
    const now = clock.getElapsedTime();
    startTime.current ??= now;
    const elapsed = now - startTime.current - delay;

    if (elapsed < 0) {
      mesh.current.visible = false;
      return;
    }

    const progress = elapsed / 1.25;
    if (progress >= 1) {
      mesh.current.visible = false;
      material.current.opacity = 0;
      active.current = false;
      return;
    }

    mesh.current.visible = true;
    mesh.current.scale.setScalar(0.7 + progress * 6.6);
    material.current.opacity = 0.42 * Math.pow(1 - progress, 1.7);
  });

  return (
    <mesh ref={mesh} visible={false} renderOrder={4}>
      <ringGeometry args={[0.34, 0.37, 72]} />
      <meshBasicMaterial
        ref={material}
        color={CEO_NODE.color}
        transparent
        opacity={0}
        blending={THREE.AdditiveBlending}
        depthTest={false}
        depthWrite={false}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

function RippleWave({ pulseSignal }: { pulseSignal: number }) {
  return (
    <group>
      <RippleRing pulseSignal={pulseSignal} delay={0} />
      <RippleRing pulseSignal={pulseSignal} delay={0.14} />
      <RippleRing pulseSignal={pulseSignal} delay={0.28} />
    </group>
  );
}

function Constellation({
  parallaxTarget,
  pulseSignal,
}: {
  parallaxTarget: MutableRefObject<ParallaxTarget>;
  pulseSignal: number;
}) {
  const group = useRef<THREE.Group>(null);
  const idleRotation = useRef(0);
  const glowTexture = useMemo(createGlowTexture, []);

  useEffect(() => () => glowTexture.dispose(), [glowTexture]);

  useFrame((_, delta) => {
    if (!group.current) return;
    idleRotation.current += delta * 0.05;
    const smoothing = 1 - Math.exp(-delta * 3.6);
    const targetX = -parallaxTarget.current.y * MAX_TILT;
    const targetY = parallaxTarget.current.x * MAX_TILT;
    const targetZ = idleRotation.current;

    group.current.rotation.x += (targetX - group.current.rotation.x) * smoothing;
    group.current.rotation.y += (targetY - group.current.rotation.y) * smoothing;
    group.current.rotation.z += (targetZ - group.current.rotation.z) * smoothing;
  });

  return (
    <>
      <ambientLight intensity={0.24} />
      <directionalLight color="#dbeafe" position={[2, 3, 5]} intensity={0.55} />
      <ParticleField />
      <group ref={group}>
        {AGENT_NODES.map((node, index) => (
          <DelegationLine key={`connection-${node.key}`} node={node} index={index} />
        ))}
        {AGENT_NODES.map((node) => (
          <AgentNode key={node.key} node={node} glowTexture={glowTexture} />
        ))}
        <CeoNode glowTexture={glowTexture} />
        <RippleWave pulseSignal={pulseSignal} />
      </group>
    </>
  );
}

/** R3F scene. Import this through HeroSceneShell or next/dynamic with ssr:false. */
export function HeroScene({ className = "h-full w-full", pulseSignal = 0 }: HeroSceneProps) {
  const container = useRef<HTMLDivElement>(null);
  const parallaxTarget = useRef<ParallaxTarget>({ x: 0, y: 0 });
  const isVisible = useIsVisible(container);

  const handlePointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.pointerType !== "mouse") return;
    const bounds = event.currentTarget.getBoundingClientRect();
    parallaxTarget.current.x = THREE.MathUtils.clamp(
      ((event.clientX - bounds.left) / Math.max(bounds.width, 1)) * 2 - 1,
      -1,
      1,
    );
    parallaxTarget.current.y = THREE.MathUtils.clamp(
      ((event.clientY - bounds.top) / Math.max(bounds.height, 1)) * 2 - 1,
      -1,
      1,
    );
  };

  const resetParallax = () => {
    parallaxTarget.current.x = 0;
    parallaxTarget.current.y = 0;
  };

  return (
    <div
      ref={container}
      aria-hidden="true"
      className={`relative overflow-hidden ${className}`}
      data-hero-canvas-active={isVisible ? "true" : "false"}
      onPointerLeave={resetParallax}
      onPointerMove={handlePointerMove}
      style={{
        background:
          "radial-gradient(circle at 50% 50%, #11192a, #0a0f1a 74%)",
      }}
    >
      <WebGLErrorBoundary>
        <SceneCanvas isVisible={isVisible}>
          <Constellation parallaxTarget={parallaxTarget} pulseSignal={pulseSignal} />
        </SceneCanvas>
      </WebGLErrorBoundary>
    </div>
  );
}

export default HeroScene;
