import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { ConfidenceBadge, Tag } from "@/components/ui/Badges";
import { BackendNotice, EmptyState } from "@/components/ui/States";
import { PageIntro } from "@/components/ui/PageIntro";
import { getEntities } from "@/lib/api";
import { humanize, shortId } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function EntitiesPage() {
  const entities = await getEntities();

  if (!entities.ok) {
    return (
      <div className="space-y-6">
        <Intro />
        <BackendNotice error={entities.error} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Intro />
      {entities.data.length === 0 ? (
        <EmptyState message="No entities yet." />
      ) : (
        <Table
          head={
            <>
              <Th>Type</Th>
              <Th>Value</Th>
              <Th>Resolution confidence</Th>
              <Th>Id</Th>
            </>
          }
        >
          {entities.data.map((e) => (
            <Tr key={e.id}>
              <Td>
                <Tag>{humanize(e.entity_type)}</Tag>
              </Td>
              <Td>
                <span className="font-medium text-ink">{e.value}</span>
              </Td>
              <Td>
                <ConfidenceBadge value={e.confidence} />
              </Td>
              <Td>
                <span className="mono text-xs text-ink-faint">{shortId(e.id)}</span>
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
      Entities are the real-world things observations reference — phone numbers, aliases,
      accounts, images, and more. They are deduplicated by type and canonical value, and
      they persist across cases.
    </PageIntro>
  );
}
