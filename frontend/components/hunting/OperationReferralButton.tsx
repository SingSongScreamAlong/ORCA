"use client";

import { useState } from "react";
import { getHuntingOperationReferral } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { EntityType, OperationReferralPackage } from "@/lib/types";

/**
 * Generate a law-enforcement referral dossier for a whole *operation* — the connected-component
 * network around a seed identifier: its member identifiers, the venues (with lawful basis), and the
 * relationship map. Bounds the case by the linked network rather than a region. Pointers/metadata
 * only (no media). The analyst reviews it inline and downloads the markdown to hand to LE.
 */
export function OperationReferralButton({
  entityType,
  value,
}: {
  entityType: EntityType;
  value: string;
}) {
  const [pkg, setPkg] = useState<OperationReferralPackage | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setBusy(true);
    setError(null);
    const res = await getHuntingOperationReferral(entityType, value);
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
    a.download = `operation-${pkg.seed_value.replace(/\W+/g, "-").toLowerCase()}.md`;
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
          className="rounded-md border border-surface-border px-3 py-1.5 text-xs font-medium text-ink-muted hover:bg-surface-sunken hover:text-ink disabled:opacity-50"
        >
          {busy ? "Building…" : pkg ? "Refresh referral" : "Generate LE referral (operation)"}
        </button>
        {pkg && (
          <button
            type="button"
            onClick={download}
            className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"
          >
            Download dossier (.md)
          </button>
        )}
        {error && <span className="text-xs text-amber-700">{error}</span>}
      </div>

      {pkg && (
        <div className="rounded-md border border-surface-border bg-surface p-3 text-xs">
          <p className="text-ink-muted">
            <span className="font-medium text-ink">{pkg.identifier_count}</span> identifier(s) ·{" "}
            <span className="font-medium text-ink">{pkg.venue_count}</span> venue(s) ·{" "}
            {pkg.relationships.length} relationship(s) · {pkg.aors.join(", ") || "—"}
          </p>
          {pkg.venues.length > 0 && (
            <ul className="mt-2 space-y-1">
              {pkg.venues.map((s) => (
                <li key={s.id} className="text-ink-muted">
                  <span className="font-medium text-ink">{s.name}</span>{" "}
                  <span className="text-ink-faint">
                    · {s.aor} · {humanize(s.category)} · lawful basis{" "}
                    {s.lawful_basis ? "recorded" : "—"}
                  </span>
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
