import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { ConfidenceBadge, OriginBadge, StatusBadge, Tag } from "@/components/ui/Badges";
import { EntityChip } from "@/components/ui/EntityChip";
import { BackendNotice, EmptyState } from "@/components/ui/States";
import { PageIntro } from "@/components/ui/PageIntro";
import { getEntities, getRelationships } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { Entity } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function RelationshipsPage() {
  const [relationships, entities] = await Promise.all([getRelationships(), getEntities()]);

  if (!relationships.ok) {
    return (
      <div className="space-y-6">
        <Intro />
        <BackendNotice error={relationships.error} status={relationships.status} />
      </div>
    );
  }

  const entityById = new Map<string, Entity>(
    entities.ok ? entities.data.map((e) => [e.id, e]) : [],
  );

  return (
    <div className="space-y-6">
      <Intro />
      {relationships.data.length === 0 ? (
        <EmptyState message="No relationships yet." />
      ) : (
        <Table
          head={
            <>
              <Th>Type</Th>
              <Th>Between</Th>
              <Th>Origin</Th>
              <Th>Support</Th>
              <Th>Status</Th>
              <Th>Confidence</Th>
            </>
          }
        >
          {relationships.data.map((r) => (
            <Tr key={r.id}>
              <Td>
                <Tag>{humanize(r.relationship_type)}</Tag>
              </Td>
              <Td>
                <div className="flex flex-wrap items-center gap-1.5">
                  <EntityChip entity={entityById.get(r.source_entity_id)} fallbackId={r.source_entity_id} />
                  <span className="text-ink-faint">—</span>
                  <EntityChip entity={entityById.get(r.target_entity_id)} fallbackId={r.target_entity_id} />
                </div>
              </Td>
              <Td>
                <OriginBadge origin={r.origin} />
              </Td>
              <Td>
                <span className="text-ink-muted">{r.observation_ids.length}</span>{" "}
                <span className="text-ink-faint">obs.</span>
              </Td>
              <Td>
                <StatusBadge status={r.status} />
              </Td>
              <Td>
                <ConfidenceBadge value={r.confidence} />
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
      Relationships are evidence-backed links between entities — the unit of discovery.
      Every relationship references the observations that support it, and nothing is
      confirmed without a human decision in the review queue.
    </PageIntro>
  );
}
