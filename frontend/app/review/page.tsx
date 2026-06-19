import { ReviewQueueItem } from "@/components/review/ReviewQueueItem";
import { BackendNotice, EmptyState } from "@/components/ui/States";
import { PageIntro } from "@/components/ui/PageIntro";
import { getEvidenceList, getReviewQueue } from "@/lib/api";
import type { EvidenceItem } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function ReviewPage() {
  const [queue, evidence] = await Promise.all([getReviewQueue(), getEvidenceList()]);

  if (!queue.ok) {
    return (
      <div className="space-y-6">
        <Intro />
        <BackendNotice error={queue.error} />
      </div>
    );
  }

  const evidenceById = new Map<string, EvidenceItem>(
    evidence.ok ? evidence.data.map((e) => [e.id, e]) : [],
  );

  return (
    <div className="space-y-6">
      <Intro />
      {queue.data.length === 0 ? (
        <EmptyState message="The review queue is empty. Nothing is awaiting a decision." />
      ) : (
        <div className="space-y-4">
          {queue.data.map((item) => (
            <ReviewQueueItem key={item.id} item={item} evidenceById={evidenceById} />
          ))}
        </div>
      )}
    </div>
  );
}

function Intro() {
  return (
    <PageIntro>
      The most important screen in ORCA. Nothing the system infers becomes confirmed
      knowledge without passing through here. Each item shows why it was surfaced, the
      supporting evidence, and its confidence — and every decision is recorded against
      the analyst who made it.
    </PageIntro>
  );
}
