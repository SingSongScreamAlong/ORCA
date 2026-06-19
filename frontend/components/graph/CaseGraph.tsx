import { humanize } from "@/lib/format";
import type { GraphView } from "@/lib/types";

/**
 * A calm, dependency-free node-link diagram of a case's approved relationships.
 * Nodes are placed evenly on a circle; edges are drawn between them. Deterministic and
 * server-rendered — no client JS, no heavy graph library.
 */
export function CaseGraph({ view }: { view: GraphView }) {
  const { nodes, edges } = view;
  const size = 560;
  const cx = size / 2;
  const cy = size / 2;
  const radius = nodes.length <= 1 ? 0 : Math.min(220, 110 + nodes.length * 10);

  const pos = new Map<string, { x: number; y: number }>();
  nodes.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
    pos.set(n.id, { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) });
  });

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      className="mx-auto h-[560px] w-full max-w-[560px]"
      role="img"
      aria-label="Relationship graph"
    >
      {/* edges */}
      {edges.map((e) => {
        const a = pos.get(e.source_entity_id);
        const b = pos.get(e.target_entity_id);
        if (!a || !b) return null;
        const mx = (a.x + b.x) / 2;
        const my = (a.y + b.y) / 2;
        return (
          <g key={e.id}>
            <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#cbd5e1" strokeWidth={1.5} />
            <text x={mx} y={my - 3} textAnchor="middle" className="fill-ink-faint text-[9px]">
              {humanize(e.relationship_type)}
            </text>
          </g>
        );
      })}
      {/* nodes */}
      {nodes.map((n) => {
        const p = pos.get(n.id);
        if (!p) return null;
        const label = n.value.length > 16 ? `${n.value.slice(0, 15)}…` : n.value;
        return (
          <g key={n.id}>
            <circle cx={p.x} cy={p.y} r={8} fill="#eaf1f8" stroke="#3b6ea5" strokeWidth={1.5} />
            <text x={p.x} y={p.y - 12} textAnchor="middle" className="fill-ink text-[11px] font-medium">
              {label}
            </text>
            <text x={p.x} y={p.y + 20} textAnchor="middle" className="fill-ink-faint text-[9px]">
              {humanize(n.entity_type)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
