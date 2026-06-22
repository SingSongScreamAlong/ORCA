import { Card } from "@/components/ui/Card";
import { CrossVenueLinks } from "@/components/hunting/CrossVenueLinks";
import { ProposeLinksButton } from "@/components/hunting/ProposeLinksButton";
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
        <div className="space-y-3">
          <ProposeLinksButton />
          <p className="text-xs text-ink-faint">
            Select an identifier to pivot — locate every venue, AOR, and lead it appears in.
          </p>
          <CrossVenueLinks identifiers={intel.cross_venue} />
        </div>
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
