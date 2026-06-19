import Link from "next/link";
import { NewCaseForm } from "@/components/cases/NewCaseForm";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { Tag } from "@/components/ui/Badges";
import { BackendNotice, EmptyState } from "@/components/ui/States";
import { PageIntro } from "@/components/ui/PageIntro";
import { getCases } from "@/lib/api";
import { formatTimestamp, humanize } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function CasesPage() {
  const cases = await getCases();

  return (
    <div className="space-y-6">
      <PageIntro>
        Cases are analyst work products — curated views over observations, relationships, and
        reports. A case is a lens, not a container: it references evidence and never owns it.
      </PageIntro>

      <NewCaseForm />

      {!cases.ok ? (
        <BackendNotice error={cases.error} />
      ) : cases.data.length === 0 ? (
        <EmptyState message="No cases yet. Create one to begin the analyst loop." />
      ) : (
        <Table
          head={
            <>
              <Th>Title</Th>
              <Th>Status</Th>
              <Th>Owner</Th>
              <Th>Updated</Th>
            </>
          }
        >
          {cases.data.map((c) => (
            <Tr key={c.id}>
              <Td>
                <Link href={`/cases/${c.id}`} className="font-medium">
                  {c.title}
                </Link>
                {c.summary && <div className="mt-0.5 text-xs text-ink-faint">{c.summary}</div>}
              </Td>
              <Td>
                <Tag>{humanize(c.status)}</Tag>
              </Td>
              <Td>{c.owner}</Td>
              <Td>{formatTimestamp(c.updated_at)}</Td>
            </Tr>
          ))}
        </Table>
      )}
    </div>
  );
}
