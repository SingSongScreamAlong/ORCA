import Link from "next/link";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { Tag } from "@/components/ui/Badges";
import { BackendNotice, EmptyState } from "@/components/ui/States";
import { PageIntro } from "@/components/ui/PageIntro";
import { getSystemAudit } from "@/lib/api";
import { humanize, shortId } from "@/lib/format";

export const dynamic = "force-dynamic";

const FILTERS: { label: string; prefix?: string }[] = [
  { label: "All" },
  { label: "Hunting Grounds", prefix: "hunting." },
  { label: "Foundry", prefix: "foundry." },
  { label: "Observations", prefix: "observation." },
];

/**
 * Admin-only system audit log — the full append-only record, including the case-less
 * integration actions (Hunting Grounds, Foundry) that the per-case audit can't show. Read-only;
 * non-admins get the calm access notice (the backend 403s).
 */
export default async function AuditPage({ searchParams }: { searchParams: { prefix?: string } }) {
  const prefix = searchParams.prefix;
  const entries = await getSystemAudit(prefix);

  if (!entries.ok) {
    return (
      <div className="space-y-6">
        <Intro />
        <BackendNotice error={entries.error} status={entries.status} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Intro />

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => {
          const active = (f.prefix ?? "") === (prefix ?? "");
          return (
            <Link
              key={f.label}
              href={f.prefix ? `/audit?prefix=${encodeURIComponent(f.prefix)}` : "/audit"}
              className={[
                "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                active
                  ? "bg-accent-soft text-accent"
                  : "border border-surface-border text-ink-muted hover:bg-surface-sunken hover:text-ink",
              ].join(" ")}
            >
              {f.label}
            </Link>
          );
        })}
      </div>

      {entries.data.length === 0 ? (
        <EmptyState message="No audit entries for this filter yet." />
      ) : (
        <Table
          head={
            <>
              <Th>When</Th>
              <Th>Actor</Th>
              <Th>Action</Th>
              <Th>Target</Th>
              <Th>Case</Th>
              <Th>Context</Th>
            </>
          }
        >
          {entries.data.map((e) => (
            <Tr key={e.id}>
              <Td>
                <span className="mono whitespace-nowrap text-xs text-ink-faint">
                  {new Date(e.created_at).toLocaleString()}
                </span>
              </Td>
              <Td>
                <span className="text-xs text-ink-muted">{e.actor_id}</span>
              </Td>
              <Td>
                <Tag>{e.action}</Tag>
              </Td>
              <Td>
                <span className="text-xs text-ink-muted">{humanize(e.target_type)}</span>
                <span className="mono ml-1 text-xs text-ink-faint">{shortId(e.target_id)}</span>
              </Td>
              <Td>
                <span className="mono text-xs text-ink-faint">
                  {e.case_id ? shortId(e.case_id) : "—"}
                </span>
              </Td>
              <Td>
                <span className="mono text-xs text-ink-faint">
                  {Object.keys(e.context).length ? JSON.stringify(e.context) : "—"}
                </span>
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
      The system-wide append-only audit log — every privileged action, attributable to who did
      it and when. This admin view includes connection/integration actions (Hunting Grounds,
      Foundry) that aren&apos;t tied to a single case. Read-only.
    </PageIntro>
  );
}
