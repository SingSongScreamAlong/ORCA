"use client";

import { useState } from "react";
import { getHuntingAorReferral } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { AorReferralPackage } from "@/lib/types";

/**
 * Generate a law-enforcement *operation rollup* for a whole AOR — every monitored venue (with
 * lawful basis), all located identifiers, and the cross-venue links that tie separate venues into
 * one operation. The regional case file. Pointers/metadata only (no media). The analyst reviews it
 * inline and downloads the markdown to hand to LE.
 */
export function AorReferralButton({ aor }: { aor: string }) {
  const [pkg, setPkg] = useState<AorReferralPackage | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setBusy(true);
    setError(null);
    const res = await getHuntingAorReferral(aor);
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setPkg(res.data);
  }

  function download() {
    if (!pkg) return;
    const blob = new Blob([pkg.summary_markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `operation-rollup-${pkg.aor.replace(/\W+/g, "-").toLowerCase()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={generate}
          disabled={busy}
          className="rounded-md border border-surface-border px-2.5 py-1 text-xs font-medium text-ink-muted hover:bg-surface-sunken hover:text-ink disabled:opacity-50"
        >
          {busy ? "Building…" : pkg ? "Refresh rollup" : "LE rollup"}
        </button>
        {pkg && (
          <button
            type="button"
            onClick={download}
            className="rounded-md bg-accent px-2.5 py-1 text-xs font-medium text-white hover:opacity-90"
          >
            Download (.md)
          </button>
        )}
        {error && <span className="text-xs text-amber-700">{error}</span>}
      </div>

      {pkg && (
        <div className="rounded-md border border-surface-border bg-surface p-3 text-xs">
          <p className="text-ink-muted">
            <span className="font-medium text-ink">{pkg.source_count}</span> venue(s) ·{" "}
            <span className="font-medium text-ink">{pkg.identifier_count}</span> identifier(s) ·{" "}
            <span className="font-medium text-accent">{pkg.cross_venue_count}</span> cross-venue
            link(s) · {pkg.lead_count} lead(s)
          </p>
          {pkg.cross_venue.length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {pkg.cross_venue.slice(0, 16).map((i) => (
                <li
                  key={`${i.entity_type}-${i.value}`}
                  className="rounded bg-accent-soft px-2 py-0.5 ring-1 ring-inset ring-accent/30"
                  title={humanize(i.entity_type)}
                >
                  <span className="mono text-ink">{i.value}</span>
                  <span className="ml-1 font-medium text-accent">×{i.source_count}</span>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-ink-faint">{pkg.notice}</p>
        </div>
      )}
    </div>
  );
}
