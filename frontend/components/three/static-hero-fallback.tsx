import { AGENT_NODES, CEO_NODE } from "./constellation-data";

export type StaticHeroFallbackProps = {
  className?: string;
  reason?: "loading" | "reduced-motion" | "no-webgl" | "webgl-error";
};

const VIEWBOX = { width: 720, height: 560, scale: 78 } as const;

function toScreen(position: readonly [number, number, number]) {
  return {
    x: VIEWBOX.width / 2 + position[0] * VIEWBOX.scale,
    y: VIEWBOX.height / 2 - position[1] * VIEWBOX.scale,
  };
}

const PARTICLES = Array.from({ length: 48 }, (_, index) => ({
  x: 18 + ((index * 97) % 684),
  y: 16 + ((index * 61) % 528),
  radius: index % 7 === 0 ? 1.4 : index % 3 === 0 ? 1 : 0.65,
  opacity: 0.14 + (index % 5) * 0.045,
}));

/** Lightweight first-paint and accessibility fallback for the WebGL scene. */
export function StaticHeroFallback({
  className = "h-full w-full",
  reason = "loading",
}: StaticHeroFallbackProps) {
  const center = toScreen(CEO_NODE.position);

  return (
    <div
      aria-hidden="true"
      className={`relative isolate overflow-hidden ${className}`}
      data-hero-mode="static"
      data-hero-reason={reason}
      style={{
        background:
          "radial-gradient(circle at 50% 50%, rgba(167,139,250,0.16), transparent 24%), radial-gradient(circle at 66% 36%, rgba(34,211,238,0.07), transparent 28%), linear-gradient(145deg, rgba(16,24,39,0.72), rgba(10,15,26,0.2))",
      }}
    >
      <div className="absolute inset-[12%] rounded-full border border-violet-300/[0.04]" />
      <div className="absolute inset-[24%] rounded-full border border-cyan-300/[0.04]" />

      <svg
        className="absolute inset-0 h-full w-full"
        viewBox={`0 0 ${VIEWBOX.width} ${VIEWBOX.height}`}
        preserveAspectRatio="xMidYMid meet"
      >
        {PARTICLES.map((particle, index) => (
          <circle
            key={index}
            cx={particle.x}
            cy={particle.y}
            r={particle.radius}
            fill="#cbd5e1"
            opacity={particle.opacity}
          />
        ))}

        {AGENT_NODES.map((node, index) => {
          const point = toScreen(node.position);
          const bendX = center.x + (point.x - center.x) * 0.48 + (index % 2 ? 22 : -22);
          const bendY = center.y + (point.y - center.y) * 0.45 - 20;

          return (
            <path
              key={`line-${node.key}`}
              d={`M ${center.x} ${center.y} Q ${bendX} ${bendY} ${point.x} ${point.y}`}
              fill="none"
              stroke={node.color}
              strokeOpacity="0.22"
              strokeWidth="1"
              vectorEffect="non-scaling-stroke"
            />
          );
        })}

        {AGENT_NODES.map((node) => {
          const point = toScreen(node.position);
          return (
            <g key={node.key}>
              <circle cx={point.x} cy={point.y} r="16" fill={node.color} opacity="0.06" />
              <circle cx={point.x} cy={point.y} r="7" fill={node.color} opacity="0.28" />
              <circle cx={point.x} cy={point.y} r="3.5" fill={node.color} opacity="0.95" />
            </g>
          );
        })}

        <circle cx={center.x} cy={center.y} r="46" fill={CEO_NODE.color} opacity="0.035" />
        <circle cx={center.x} cy={center.y} r="25" fill={CEO_NODE.color} opacity="0.08" />
        <circle cx={center.x} cy={center.y} r="11" fill={CEO_NODE.color} opacity="0.35" />
        <circle cx={center.x} cy={center.y} r="6" fill={CEO_NODE.color} />
      </svg>

      <div className="absolute inset-x-1/4 bottom-[9%] h-px bg-gradient-to-r from-transparent via-violet-300/15 to-transparent" />
    </div>
  );
}

export default StaticHeroFallback;
