import { Card } from "@/components/ui/Card";
import { ProposeLinksButton } from "@/components/hunting/ProposeLinksButton";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { humanize } from "@/lib/format";
import type { HuntingIntelPicture } from "@/lib/types";

/**
 * AOR intelligence — the common operating picture. Surfaces the identifiers ORCA located that
 * recur across two or more monitored venues: a phone, wallet, handle, or .onion seen in multiple
 * places is the strongest signal that separate listings are one operation. Read-only; pointers
 * and metadata only (no media). This is where located leads become a case.
 */
export function IntelPicture({ intel }: { intel: HuntingIntelPicture }) {
  return (
    <Card
      title="AOR intelligence — cross-venue links"
      subtitle="Identifiers located from two or more monitored venues — the strongest case-building leads. The same phone, wallet, handle, or .onion across multiple places suggests one operation. Read-only."
    >
      <div className="mb-3 flex flex-wrap gap-4 text-xs text-ink-muted">
        <Stat label="Monitored venues" value={intel.monitored_sources} />
        <Stat label="Leads" value={intel.leads} />
        <Stat label="Located identifiers" value={intel.identifiers} />
        <Stat label="Cross-venue links" value={intel.cross_venue_count} accent />
      </div>

      {intel.cross_venue.length === 0 ? (
        <p className="text-xs text-ink-faint">
          No cross-venue links yet — identifiers located so far appear in a single venue. As
          collection runs, recurring phones/wallets/handles will surface here.
        </p>
      ) : (
        <>
          <ProposeLinksButton />
        <Table
          head={
            <>
              <Th>Identifier</Th>
              <Th>Type</Th>
              <Th>Venues</Th>
              <Th>Leads</Th>
              <Th>Seen across</Th>
            </>
          }
        >
          {intel.cross_venue.map((i, idx) => (
            <Tr key={idx}>
              <Td>
                <span className="mono text-xs text-ink">{i.value}</span>
              </Td>
              <Td>
                <span className="text-xs text-ink-muted">{humanize(i.entity_type)}</span>
              </Td>
              <Td>
                <span className="inline-flex items-center rounded bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent">
                  {i.source_count} venues
                </span>
              </Td>
              <Td>
                <span className="tabular-nums text-xs text-ink-muted">{i.lead_count}</span>
              </Td>
              <Td>
                <span className="text-xs text-ink-faint">{i.sources.join(" · ")}</span>
              </Td>
            </Tr>
          ))}
        </Table>
        </>
      )}
    </Card>
  );
}

function Stat({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div>
      <div className={`text-lg font-semibold ${accent ? "text-accent" : "text-ink"}`}>{value}</div>
      <div className="text-ink-faint">{label}</div>
    </div>
  );
}
