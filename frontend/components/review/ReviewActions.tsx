"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCan } from "@/components/auth/UserContext";
import { decideReview } from "@/lib/api";
import type { ReviewDecision } from "@/lib/types";

/**
 * The analyst decision controls — role-aware. Only users who can review see the
 * buttons. If a decision is blocked by self-review and the user is an admin, it is
 * retried as an explicit override.
 */
export function ReviewActions({ itemId }: { itemId: string }) {
  const router = useRouter();
  const canDecide = useCan("review_decide");
  const canOverride = useCan("admin_override");
  const [busy, setBusy] = useState<ReviewDecision | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!canDecide) {
    return (
      <p className="text-xs text-ink-faint">
        Review decisions require a reviewer role. You can view the evidence but not decide.
      </p>
    );
  }

  async function decide(decision: ReviewDecision) {
    setBusy(decision);
    setError(null);
    let result = await decideReview(itemId, decision);
    if (!result.ok && result.status === 403 && canOverride) {
      result = await decideReview(itemId, decision, "admin override", true);
    }
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
