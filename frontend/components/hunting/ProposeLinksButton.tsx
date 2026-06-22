"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCan } from "@/components/auth/UserContext";
import { proposeHuntingLinks } from "@/lib/api";

/**
 * Propose cross-venue links into the review queue. For identifier pairs that co-occur in approved
 * leads across two or more monitored venues, ORCA proposes an `appears_with` relationship for an
 * analyst to confirm. Only approved evidence is cited; nothing is auto-confirmed.
 */
export function ProposeLinksButton() {
  const router = useRouter();
  const canRun = useCan("create_observation");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!canRun) return null;

  async function propose() {
    setBusy(true);
    setError(null);
    setNote(null);
    const res = await proposeHuntingLinks();
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setNote(
      res.data.proposed > 0
        ? `Proposed ${res.data.proposed} cross-venue link(s) to the review queue for an analyst to confirm.`
        : "No new cross-venue links to propose (need pairs co-occurring in approved leads across 2+ venues).",
    );
    router.refresh();
  }

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      <button
        type="button"
        onClick={propose}
        disabled={busy}
        className="rounded-md border border-accent px-3 py-1.5 text-sm font-medium text-accent hover:bg-accent-soft disabled:opacity-50"
      >
        {busy ? "Proposing…" : "Suggest cross-venue links"}
      </button>
      {note && <span className="text-xs text-green-700">{note}</span>}
      {error && <span className="text-xs text-amber-700">{error}</span>}
    </div>
  );
}
