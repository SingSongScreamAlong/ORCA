"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { decideReview } from "@/lib/api";
import type { ReviewDecision } from "@/lib/types";

/**
 * The three analyst actions on a review item. This is where "analysts decide"
 * happens: each action posts a decision to the backend, which records it in the
 * append-only audit log, then the view refreshes.
 */
export function ReviewActions({ itemId }: { itemId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState<ReviewDecision | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function decide(decision: ReviewDecision) {
    setBusy(decision);
    setError(null);
    const result = await decideReview(itemId, decision);
    setBusy(null);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    router.refresh();
  }

  const base =
    "rounded-md px-3 py-1.5 text-sm font-medium ring-1 ring-inset transition-colors disabled:opacity-50";

  return (
    <div className="flex flex-col items-end gap-2">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => decide("approve")}
          disabled={busy !== null}
          className={`${base} bg-green-50 text-green-700 ring-green-200 hover:bg-green-100`}
        >
          {busy === "approve" ? "Approving…" : "Approve"}
        </button>
        <button
          type="button"
          onClick={() => decide("needs_more_review")}
          disabled={busy !== null}
          className={`${base} bg-sky-50 text-sky-700 ring-sky-200 hover:bg-sky-100`}
        >
          Needs more review
        </button>
        <button
          type="button"
          onClick={() => decide("reject")}
          disabled={busy !== null}
          className={`${base} bg-surface text-ink-muted ring-surface-border hover:bg-surface-sunken`}
        >
          Reject
        </button>
      </div>
      {error && <p className="text-xs text-amber-700">{error}</p>}
    </div>
  );
}
