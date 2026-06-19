import { humanize, shortId } from "@/lib/format";
import type { Entity } from "@/lib/types";

/** Compact representation of an entity: its type and canonical value. */
export function EntityChip({ entity, fallbackId }: { entity?: Entity; fallbackId?: string }) {
  if (!entity) {
    return <span className="mono text-xs text-ink-faint">{shortId(fallbackId ?? "")}</span>;
  }
  return (
    <span className="inline-flex items-baseline gap-1 rounded bg-surface-sunken px-2 py-0.5 text-xs ring-1 ring-inset ring-surface-border">
      <span className="text-ink-faint">{humanize(entity.entity_type)}</span>
      <span className="font-medium text-ink">{entity.value}</span>
    </span>
  );
}
