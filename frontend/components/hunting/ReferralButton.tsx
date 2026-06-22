"use client";

import { useState } from "react";
import { getHuntingReferral } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { HuntingReferralPackage } from "@/lib/types";

/**
 * Generate a law-enforcement referral dossier for a source — the located identifiers, text leads,
 * and relationship map, with provenance and lawful basis. Pointers/metadata only (no media). The
 * analyst can review it inline and download the markdown to hand to LE.
 */
export function ReferralButton({ sourceId }: { sourceId: string }) {
  const [pkg, setPkg] = useState<HuntingReferralPackage | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setBusy(true);
    setError(null);
    const res = await getHuntingReferral(sourceId);
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
    a.download = `referral-${pkg.source.name.replace(/\W+/g, "-").toLowerCase()}.md`;
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
          className="rounded-md border border-surface-border px-3 py-1.5 text-sm font-medium text-ink-muted hover:bg-surface-sunken hover:text-ink disabled:opacity-50"
        >
          {busy ? "Building…" : pkg ? "Refresh referral" : "Generate LE referral"}
        </button>
        {pkg && (
          <button
            type="button"
            onClick={download}
            className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90"
          >
            Download dossier (.md)
          </button>
        )}
        {error && <span className="text-xs text-amber-700">{error}</span>}
      </div>

      {pkg && (
        <div className="rounded-md border border-surface-border bg-surface-sunken p-3 text-xs">
          <p className="text-ink-muted">
            <span className="font-medium text-ink">{pkg.identifier_count}</span> located
            identifier(s) · <span className="font-medium text-ink">{pkg.observation_count}</span>{" "}
            text lead(s) · {pkg.relationships.length} relationship(s)
          </p>
          {pkg.located_identifiers.length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {pkg.located_identifiers.slice(0, 24).map((i, idx) => (
                <li
                  key={idx}
                  className="rounded bg-surface px-2 py-0.5 ring-1 ring-inset ring-surface-border"
                  title={humanize(i.entity_type)}
                >
                  <span className="text-ink-faint">{humanize(i.entity_type)}:</span>{" "}
                  <span className="mono text-ink">{i.value}</span>
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
