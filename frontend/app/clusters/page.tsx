import { Card } from "@/components/ui/Card";
import { ConfidenceBadge, OriginBadge, Tag } from "@/components/ui/Badges";
import { BackendNotice, EmptyState } from "@/components/ui/States";
import { PageIntro } from "@/components/ui/PageIntro";
import { getClusters } from "@/lib/api";
import { humanize } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function ClustersPage() {
  const clusters = await getClusters();

  if (!clusters.ok) {
    return (
      <div className="space-y-6">
        <Intro />
        <BackendNotice error={clusters.error} status={clusters.status} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Intro />
      {clusters.data.length === 0 ? (
        <EmptyState message="No clusters yet." />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {clusters.data.map((c) => (
            <Card key={c.id} title={c.title}>
              <div className="flex flex-wrap items-center gap-2">
                <Tag>{humanize(c.status)}</Tag>
                <OriginBadge origin={c.origin} />
              </div>
              <dl className="mt-4 grid grid-cols-3 gap-4 text-sm">
                <div>
                  <dt className="label">Entities</dt>
                  <dd className="mt-1 text-lg font-semibold tabular-nums text-ink">
                    {c.entity_ids.length}
                  </dd>
                </div>
                <div>
                  <dt className="label">Observations</dt>
                  <dd className="mt-1 text-lg font-semibold tabular-nums text-ink">
                    {c.observation_ids.length}
                  </dd>
                </div>
                <div>
                  <dt className="label">Confidence</dt>
                  <dd className="mt-1">
                    <ConfidenceBadge value={c.confidence} />
                  </dd>
                </div>
              </dl>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function Intro() {
  return (
    <PageIntro>
      Clusters group related entities and observations into candidate patterns. They can
      be proposed by the system or assembled by an analyst — and they group existing
      evidence rather than owning it.
    </PageIntro>
  );
}
