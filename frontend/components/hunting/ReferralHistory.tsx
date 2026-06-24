import { Card } from "@/components/ui/Card";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { humanize } from "@/lib/format";
import type { HuntingReferralRecord } from "@/lib/types";

/**
 * Referral history — the accountability view over the four referral tiers (source, identifier, AOR,
 * operation). Read from the append-only audit trail: it records that a dossier was handed to LE — at
 * what scope, for what subject, by whom, and when — never the dossier's contents. Counts only.
 */
const TIER_STYLE: Record<string, string> = {
  source: "bg-slate-100 text-slate-700 ring-slate-200",
  identifier: "bg-sky-50 text-sky-700 ring-sky-200",
  aor: "bg-violet-50 text-violet-700 ring-violet-200",
  operation: "bg-accent-soft text-accent ring-accent/30",
};

export function ReferralHistory({ records }: { records: HuntingReferralRecord[] }) {
  if (records.length === 0) return null;
  return (
    <Card
      title="Referrals handed to law enforcement"
      subtitle="Every dossier generated, at what scope and for what subject, by whom and when — read from the append-only audit trail. Pointers and counts only; never the dossier's contents."
    >
      <Table
        head={
          <>
            <Th>Scope</Th>
            <Th>Subject</Th>
            <Th>Summary</Th>
            <Th>By</Th>
            <Th>When</Th>
          </>
        }
      >
        {records.map((r, i) => (
          <Tr key={i}>
            <Td>
              <span
                className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${
                  TIER_STYLE[r.tier] ?? "bg-surface-sunken text-ink-muted ring-surface-border"
                }`}
              >
                {humanize(r.tier)}
              </span>
            </Td>
            <Td>
              <span className="mono text-xs text-ink">{r.target}</span>
            </Td>
            <Td>
              <span className="text-xs text-ink-muted">{r.summary}</span>
            </Td>
            <Td>
              <span className="text-xs text-ink-muted">{r.generated_by}</span>
            </Td>
            <Td>
              <span className="mono text-xs text-ink-faint">
                {new Date(r.generated_at).toLocaleString()}
              </span>
            </Td>
          </Tr>
        ))}
      </Table>
    </Card>
  );
}
