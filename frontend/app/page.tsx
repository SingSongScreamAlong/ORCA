import Link from "next/link";
import { StatCard } from "@/components/dashboard/StatCard";
import { Card } from "@/components/ui/Card";
import { ConfidenceBadge, OriginBadge, StatusBadge, Tag } from "@/components/ui/Badges";
import { BackendNotice, EmptyState } from "@/components/ui/States";
import { PageIntro } from "@/components/ui/PageIntro";
import { getDashboard } from "@/lib/api";
import { formatTimestamp, humanize, shortId } from "@/lib/format";

// Always render against live data.
export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const result = await getDashboard();

  if (!result.ok) {
    return (
      <div className="space-y-6">
        <PageIntro>
          The dashboard answers three questions: what is new, what changed, and what
          requires review.
        </PageIntro>
        <BackendNotice error={result.error} status={result.status} />
      </div>
    );
  }

  const { counts, recent_observations, recent_relationships, review_queue, hunting, system_health } =
    result.data;

  return (
    <div className="space-y-6">
      <PageIntro>
        The dashboard answers three questions: what is new, what changed, and what
        requires review.
      </PageIntro>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Cases" value={counts.cases} hint="Analyst work products" />
        <StatCard label="Observations" value={counts.observations} hint="Recorded facts" />
        <StatCard label="Relationships" value={counts.relationships} hint="Discovered links" />
        <StatCard
          label="Awaiting review"
          value={counts.pending_review}
          hint="In the review queue"
          emphasis
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Recent observations" subtitle="What is new">
          {recent_observations.length === 0 ? (
            <EmptyState message="No observations yet." />
          ) : (
            <ul className="text-sm">
              {recent_observations.map((o) => (
                <li key={o.id} className="table-row flex items-start justify-between gap-4 py-2.5">
                  <div className="min-w-0">
                    <div className="truncate text-ink">{o.notes ?? "(no notes)"}</div>
                    <div className="mt-0.5 text-xs text-ink-faint">
                      <span className="mono">{shortId(o.id)}</span> · {o.collector} ·{" "}
                      {formatTimestamp(o.timestamp)}
                    </div>
                  </div>
                  <ConfidenceBadge value={o.confidence} />
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Recent relationships" subtitle="What changed">
          {recent_relationships.length === 0 ? (
            <EmptyState message="No relationships yet." />
          ) : (
            <ul className="text-sm">
              {recent_relationships.map((r) => (
                <li key={r.id} className="table-row flex items-center justify-between gap-4 py-2.5">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <Tag>{humanize(r.relationship_type)}</Tag>
                      <StatusBadge status={r.status} />
                    </div>
                    <div className="mt-1 text-xs text-ink-faint">
                      <OriginBadge origin={r.origin} /> ·{" "}
                      {r.observation_ids.length} supporting observation(s)
                    </div>
                  </div>
                  <ConfidenceBadge value={r.confidence} />
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card
        title="Review queue"
        subtitle="What requires review"
        actions={
          <Link href="/review" className="text-sm font-medium">
            Open queue →
          </Link>
        }
      >
        {review_queue.length === 0 ? (
          <EmptyState message="The review queue is empty." />
        ) : (
          <ul className="text-sm">
            {review_queue.map((item) => (
              <li key={item.id} className="table-row flex items-start justify-between gap-4 py-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Tag>{humanize(item.item_type)}</Tag>
                    <StatusBadge status={item.status} />
                  </div>
                  <p className="mt-1.5 max-w-2xl text-ink-muted">{item.rationale}</p>
                </div>
                <ConfidenceBadge value={item.confidence} />
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card
        title="Hunting Grounds"
        subtitle="Reconnaissance posture — venues watched, leads located, and the cross-venue links that build cases"
        actions={
          <Link href="/hunting" className="text-sm font-medium">
            Open Hunting Grounds →
          </Link>
        }
      >
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard label="Monitored venues" value={hunting.monitored_sources} hint={`of ${hunting.total_sources} in registry`} />
          <StatCard label="Leads located" value={hunting.leads} hint="text/metadata only" />
          <StatCard label="Cross-venue links" value={hunting.cross_venue_links} hint="recurring identifiers" emphasis />
          <StatCard label="AORs" value={hunting.aors} hint="areas with venues" />
        </div>
        {hunting.top_cross_venue.length > 0 && (
          <ul className="mt-4 space-y-1.5 text-sm">
            {hunting.top_cross_venue.map((i, idx) => (
              <li key={idx} className="table-row flex items-center justify-between gap-4 py-1.5">
                <div className="min-w-0">
                  <span className="text-xs text-ink-faint">{humanize(i.entity_type)}:</span>{" "}
                  <span className="mono text-ink">{i.value}</span>
                </div>
                <span className="inline-flex items-center rounded bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent">
                  {i.source_count} venues
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="System health">
        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                system_health.status === "ok" ? "bg-green-500" : "bg-amber-500"
              }`}
            />
            <span className="text-ink">API {humanize(system_health.status)}</span>
          </div>
          <div className="text-ink-faint">
            Storage backend:{" "}
            <span className="mono text-ink-muted">{system_health.storage_backend}</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
