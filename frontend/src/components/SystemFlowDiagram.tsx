import type { SystemMetrics } from "@/types";

const NODE_W = 170;
const NODE_H = 58;

function Node({
  x,
  y,
  label,
  sub,
  tone = "default",
}: {
  x: number;
  y: number;
  label: string;
  sub?: string;
  tone?: "default" | "signal" | "info" | "warn";
}) {
  const stroke = { default: "#2A3744", signal: "#27E6A6", info: "#5B8DEF", warn: "#F5B544" }[tone];
  const labelColor = { default: "#E7EDF3", signal: "#27E6A6", info: "#5B8DEF", warn: "#F5B544" }[tone];
  return (
    <g transform={`translate(${x}, ${y})`}>
      <rect width={NODE_W} height={NODE_H} rx={10} fill="#11161D" stroke={stroke} strokeWidth={1.2} />
      <text
        x={NODE_W / 2}
        y={NODE_H / 2 - (sub ? 6 : 0)}
        textAnchor="middle"
        fontSize="12"
        fontWeight={600}
        fill={labelColor}
        fontFamily="Inter, sans-serif"
      >
        {label}
      </text>
      {sub && (
        <text
          x={NODE_W / 2}
          y={NODE_H / 2 + 12}
          textAnchor="middle"
          fontSize="10.5"
          fill="#8A97A6"
          fontFamily="JetBrains Mono, monospace"
        >
          {sub}
        </text>
      )}
    </g>
  );
}

function FlowEdge({
  d,
  color = "#2A3744",
  animated = false,
  dur = "1.6s",
}: {
  d: string;
  color?: string;
  animated?: boolean;
  dur?: string;
}) {
  return (
    <g>
      <path d={d} stroke={color} strokeWidth={1.4} fill="none" opacity={0.6} />
      {animated && (
        <circle r={3} fill={color}>
          <animateMotion dur={dur} repeatCount="indefinite" path={d} />
        </circle>
      )}
    </g>
  );
}

export function SystemFlowDiagram({ metrics }: { metrics: SystemMetrics }) {
  const hitPct = Math.round(metrics.cache.hit_rate * 100);
  const aliveWorkers = metrics.workers.filter((w) => w.alive).length;

  return (
    <div className="card overflow-x-auto p-5">
      <h2 className="mb-1 text-sm font-medium text-ink">Request flow</h2>
      <p className="mb-4 text-xs text-muted">
        Live topology — redirect reads hit Redis first; misses read through the PostgreSQL Read Replica. Click events publish
        to RabbitMQ and are processed asynchronously by the worker pool writing to the Primary PostgreSQL database.
      </p>
      <svg viewBox="0 0 1000 320" className="min-w-[860px]" role="img" aria-label="System request flow diagram">
        {/* Connection paths */}
        <FlowEdge d="M 190 139 C 240 139, 250 69, 280 69" color="#27E6A6" animated dur="1.2s" />
        <FlowEdge d="M 190 139 C 240 139, 250 209, 280 209" color="#5B8DEF" animated dur="1.8s" />
        <FlowEdge d="M 450 209 C 510 209, 530 119, 570 119" color="#2A3744" />
        <FlowEdge d="M 655 55 V 90" color="#F5B544" animated dur="2.0s" />
        <FlowEdge d="M 450 209 H 570" color="#5B8DEF" animated dur="1.5s" />
        <FlowEdge d="M 740 209 H 800" color="#27E6A6" animated dur="1.2s" />
        <FlowEdge d="M 885 183 C 885 100, 780 29, 740 29" color="#2A3744" />
        <FlowEdge d="M 885 238 V 275 H 740" color="#FF6B5B" />

        {/* Nodes */}
        <Node x={20} y={110} label="Client" sub="browser" />
        <Node x={280} y={40} label="Redis Cache" sub={`hit rate ${hitPct}%`} tone="signal" />
        <Node x={280} y={180} label="Redirect API" sub="fire-and-forget publish" tone="info" />
        <Node x={570} y={0} label="Postgres (Primary)" sub="writes & upserts" tone="default" />
        <Node x={570} y={90} label="Postgres (Replica)" sub="read-only queries" tone="default" />
        <Node x={570} y={180} label="RabbitMQ" sub={`depth ${metrics.queue.queue_depth}`} tone="info" />
        <Node x={570} y={248} label="DLQ" sub={`${metrics.queue.dlq_depth} dead-lettered`} tone={metrics.queue.dlq_depth > 0 ? "warn" : "default"} />
        <Node x={800} y={180} label="Worker pool" sub={`${aliveWorkers} alive`} tone={aliveWorkers > 0 ? "signal" : "warn"} />
      </svg>
    </div>
  );
}

