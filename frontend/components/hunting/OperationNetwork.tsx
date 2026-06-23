"use client";

import { useState } from "react";
import { getHuntingOperationCluster } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { EntityType, OperationCluster } from "@/lib/types";

/**
 * The *operation* around an identifier — its connected component. Where the co-occurring chips show
 * the direct (1-hop) link candidates, this reveals the full transitive network: every identifier
 * tied to the seed through shared leads or relationships, the venues and AORs it touches. The seam
 * that says these scattered listings are one operation, regardless of AOR. Read-only; pointers only.
 */
export function OperationNetwork({
  entityType,
  value,
}: {
  entityType: EntityType;
  value: string;
}) {
  const [cluster, setCluster] = useState<OperationCluster | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function reveal() {
    if (cluster) {
      setCluster(null);
      return;
    }
    setBusy(true);
    setError(null);
    const res = await getHuntingOperationCluster(entityType, value);
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setCluster(res.data);
  }

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={reveal}
        disabled={busy}
        aria-expanded={cluster !== null}
        className="rounded-md border border-surface-border px-3 py-1.5 text-xs font-medium text-ink-muted hover:bg-surface-sunken hover:text-ink disabled:opacity-50"
      >
        {busy ? "Tracing…" : cluster ? "Hide operation network" : "Reveal operation network"}
      </button>
      {error && <p className="text-xs text-amber-700">{error}</p>}

      {cluster && (
        <div className="space-y-2 rounded-md border border-surface-border bg-surface p-3 text-xs">
          <p className="text-ink-muted">
            <span className="font-medium text-ink">{cluster.identifier_count}</span> identifier(s) ·{" "}
            <span className="font-medium text-ink">{cluster.venue_count}</span> venue(s) ·{" "}
            {cluster.lead_count} lead(s) · {cluster.aors.join(", ") || "—"}
            {cluster.relationships.length > 0 && ` · ${cluster.relationships.length} relationship(s)`}
            {cluster.truncated && (
              <span className="ml-1 text-amber-700">(network capped — very large)</span>
            )}
          </p>
          <ul className="flex flex-wrap gap-1.5">
            {cluster.members.map((m, idx) => {
              const isSeed = m.entity_type === entityType && m.value === value;
              return (
                <li
                  key={`${m.entity_type}-${m.value}-${idx}`}
                  className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 ${
                    isSeed
                      ? "border-accent/40 bg-accent-soft"
                      : "border-surface-border bg-surface-sunken"
                  }`}
                  title={`${m.venue_count} venue(s) · ${m.lead_count} lead(s)`}
                >
                  <span className="mono text-ink">{m.value}</span>
                  <span className="text-ink-faint">{humanize(m.entity_type)}</span>
                  {isSeed && <span className="font-medium text-accent">seed</span>}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
