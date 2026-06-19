import Link from "next/link";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { ConfidenceBadge, StatusBadge } from "@/components/ui/Badges";
import { EntityChip } from "@/components/ui/EntityChip";
import { BackendNotice, EmptyState } from "@/components/ui/States";
import { PageIntro } from "@/components/ui/PageIntro";
import { getEntities, getObservations, getSources } from "@/lib/api";
import { formatTimestamp, shortId } from "@/lib/format";
import type { Entity, Source } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function ObservationsPage() {
  const [observations, sources, entities] = await Promise.all([
    getObservations(),
    getSources(),
    getEntities(),
  ]);

  if (!observations.ok) {
    return (
      <div className="space-y-6">
        <Intro />
        <BackendNotice error={observations.error} />
      </div>
    );
  }

  const sourceById = new Map<string, Source>(
    sources.ok ? sources.data.map((s) => [s.id, s]) : [],
  );
  const entityById = new Map<string, Entity>(
    entities.ok ? entities.data.map((e) => [e.id, e]) : [],
  );

  return (
    <div className="space-y-6">
      <Intro />
      <Link
        href="/intake"
        className="inline-block rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
      >
        + Intake observation
      </Link>
      {observations.data.length === 0 ? (
        <EmptyState message="No observations recorded yet." />
      ) : (
        <Table
          head={
            <>
              <Th>Observation</Th>
              <Th>Status</Th>
              <Th>Source</Th>
              <Th>Observed</Th>
              <Th>References</Th>
              <Th>Confidence</Th>
            </>
          }
        >
          {observations.data.map((o) => (
            <Tr key={o.id}>
              <Td>
                <div className="max-w-md text-ink">{o.notes ?? "(no notes)"}</div>
                <div className="mono mt-0.5 text-xs text-ink-faint">{shortId(o.id)}</div>
              </Td>
              <Td>
                <StatusBadge status={o.status} />
              </Td>
              <Td>{sourceById.get(o.source_id)?.name ?? shortId(o.source_id)}</Td>
              <Td>{formatTimestamp(o.timestamp)}</Td>
              <Td>
                <div className="flex flex-wrap gap-1">
                  {o.entity_ids.map((id) => (
                    <EntityChip key={id} entity={entityById.get(id)} fallbackId={id} />
                  ))}
                </div>
              </Td>
              <Td>
                <ConfidenceBadge value={o.confidence} />
              </Td>
            </Tr>
          ))}
        </Table>
      )}
    </div>
  );
}

function Intro() {
  return (
    <PageIntro>
      Observations are the atomic unit of truth — a single recorded fact, attributed to
      a source and a collector, supported by evidence. They are append-only: corrections
      are new observations, never edits.
    </PageIntro>
  );
}
