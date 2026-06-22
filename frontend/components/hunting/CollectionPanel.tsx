"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCan } from "@/components/auth/UserContext";
import { runHuntingCollection } from "@/lib/api";
import type { HuntingCollectionStatus } from "@/lib/types";

/**
 * Automated collection — pull text-only candidate leads from every monitored source and propose
 * each as an observation in the review queue (analysts decide). CSAM-safe by construction (no
 * media field); runs only against monitored sources. Disabled until a licensed source is
 * configured. This is first-pass triage, automated — it never auto-approves anything.
 */
export function CollectionPanel({ status }: { status: HuntingCollectionStatus | null }) {
  const router = useRouter();
  const canRun = useCan("create_observation");
  const [limit, setLimit] = useState(10);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  if (!canRun) return null;
  const enabled = status?.enabled ?? false;

  async function collectAll() {
    setBusy(true);
    setError(null);
    setNote(null);
    const res = await runHuntingCollection(limit);
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setNote(
      `Collected from ${res.data.sources_collected} monitored source(s) via ${res.data.provider ?? "provider"} — proposed ${res.data.total_proposed} observation(s) to the review queue.`,
    );
    router.refresh();
  }

  return (
    <div className="space-y-3">
      <ProviderState status={status} />
      <div className="flex flex-wrap items-end gap-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-muted">Max leads / source</label>
          <input
            type="number"
            min={1}
            max={50}
            value={limit}
            onChange={(e) => setLimit(Math.max(1, Math.min(50, Number(e.target.value) || 1)))}
            className="w-28 rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
          />
        </div>
        <button
          type="button"
          onClick={collectAll}
          disabled={busy || !enabled}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "Collecting…" : "Collect from all monitored"}
        </button>
      </div>
      {note && <p className="text-xs text-green-700">{note} Each still needs analyst review.</p>}
      {error && <p className="text-xs text-amber-700">{error}</p>}
    </div>
  );
}

function ProviderState({ status }: { status: HuntingCollectionStatus | null }) {
  if (!status || status.provider === "disabled") {
    return (
      <p className="rounded-md border border-surface-border bg-surface-sunken px-3 py-2 text-xs text-ink-muted">
        Automated collection is <span className="font-medium">disabled</span>. It turns on only when
        a licensed source is configured (<code className="mono">ORCA_HUNTING_COLLECTION_PROVIDER</code>)
        with a recorded lawful basis — see{" "}
        <a
          className="text-accent hover:underline"
          href="https://github.com/SingSongScreamAlong/ORCA/blob/main/docs/hunting_grounds_collection.md"
        >
          the collection guide
        </a>
        . Leads are text-only (CSAM-safe) and enter the review queue as proposals.
      </p>
    );
  }
  const tone = status.configured
    ? "border-green-200 bg-green-50 text-green-800"
    : "border-amber-200 bg-amber-50 text-amber-800";
  return (
    <p className={`rounded-md border px-3 py-2 text-xs ${tone}`}>
      Provider <span className="mono font-medium">{status.provider}</span>
      {status.host ? (
        <>
          {" "}
          · <span className="mono">{status.host}</span>
        </>
      ) : null}{" "}
      · lawful basis {status.lawful_basis_recorded ? "recorded" : "not recorded"}
      {status.tor_enabled ? " · via Tor (dark web)" : ""}
      {status.configured ? "" : " · not fully configured"}. Text-only leads → proposed observations.
    </p>
  );
}
