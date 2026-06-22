"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCan } from "@/components/auth/UserContext";
import { collectHuntingSource } from "@/lib/api";

/**
 * Trigger automated collection from a single monitored source — pulls text-only leads and
 * proposes them as observations in the review queue. Disabled-by-default collection surfaces a
 * calm message if it isn't configured. Analysts still decide on every proposed observation.
 */
export function CollectSourceButton({ sourceId }: { sourceId: string }) {
  const router = useRouter();
  const canRun = useCan("create_observation");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!canRun) return null;

  async function collect() {
    setBusy(true);
    setError(null);
    setMsg(null);
    const res = await collectHuntingSource(sourceId, 10);
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setMsg(`Proposed ${res.data.proposed_observation_ids.length} observation(s) to review.`);
    router.refresh();
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        onClick={collect}
        disabled={busy}
        className="rounded-md border border-surface-border px-3 py-1.5 text-sm font-medium text-ink-muted hover:bg-surface-sunken hover:text-ink disabled:opacity-50"
      >
        {busy ? "Collecting…" : "Collect leads now"}
      </button>
      {msg && <span className="text-xs text-green-700">{msg}</span>}
      {error && <span className="text-xs text-amber-700">{error}</span>}
    </div>
  );
}
