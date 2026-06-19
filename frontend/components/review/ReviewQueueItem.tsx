import { ConfidenceBadge, StatusBadge, Tag } from "@/components/ui/Badges";
import { ReviewActions } from "@/components/review/ReviewActions";
import { formatTimestamp, humanize, shortId } from "@/lib/format";
import type { Evidence, ReviewItem } from "@/lib/types";

/**
 * One review-queue item. Every item shows the four things an analyst needs to decide:
 * why it was surfaced, the supporting evidence, the confidence, and the actions.
 */
export function ReviewQueueItem({
  item,
  evidenceById,
}: {
  item: ReviewItem;
  evidenceById: Map<string, Evidence>;
}) {
  const decided = item.status !== "proposed" && item.status !== "needs_review";
  const evidence = item.evidence_ids
    .map((id) => evidenceById.get(id))
    .filter((e): e is Evidence => Boolean(e));

  return (
    <article className="card">
      <div className="flex items-start justify-between gap-6">
        <div className="min-w-0 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Tag>{humanize(item.item_type)}</Tag>
            <StatusBadge status={item.status} />
            <span className="text-xs text-ink-faint">
              <span className="mono">{shortId(item.subject_id)}</span> · {item.subject_type}
            </span>
          </div>

          {/* Why it was surfaced — always present. */}
          <div>
            <div className="label">Why this was surfaced</div>
            <p className="mt-1 max-w-3xl text-sm text-ink">{item.rationale}</p>
          </div>

          {/* Supporting evidence. */}
          <div>
            <div className="label">Supporting evidence</div>
            {evidence.length === 0 ? (
              <p className="mt-1 text-sm text-ink-faint">No linked evidence.</p>
            ) : (
              <ul className="mt-1 space-y-1">
                {evidence.map((e) => (
                  <li key={e.id} className="flex items-center gap-2 text-sm">
                    <Tag>{humanize(e.evidence_type)}</Tag>
                    <span className="mono text-ink-muted">{e.sha256.slice(0, 12)}…</span>
                    <span className="text-ink-faint">{e.description ?? e.storage_uri}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="flex shrink-0 flex-col items-end gap-3">
          <div className="text-right">
            <div className="label">Confidence</div>
            <div className="mt-1">
              <ConfidenceBadge value={item.confidence} />
            </div>
          </div>

          {decided ? (
            <div className="text-right text-xs text-ink-faint">
              {humanize(item.status)}
              {item.decided_by ? ` by ${item.decided_by}` : ""}
              {item.decided_at ? (
                <>
                  <br />
                  {formatTimestamp(item.decided_at)}
                </>
              ) : null}
            </div>
          ) : (
            <ReviewActions itemId={item.id} />
          )}
        </div>
      </div>
    </article>
  );
}
