"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "@/components/auth/UserContext";
import { importHuntingSources } from "@/lib/api";
import type { HuntingSourceCategory } from "@/lib/types";

/**
 * Bring-your-own hunting list. An administrator pastes the sites to monitor (one per line,
 * `name | url` or a bare URL) and the lawful basis they're watched under; each is proposed
 * (deduped by URL), authorized with that shared record, and set monitored in one pass. This is the
 * authorization-first gate done in bulk — the lawful-basis record is still mandatory, just shared
 * across the list. Admin-only.
 */
const CATEGORIES: HuntingSourceCategory[] = [
  "escort_listing",
  "classified",
  "forum",
  "social",
  "aggregator",
  "other",
];

export function ImportSitesForm({ defaultAor }: { defaultAor: string }) {
  const user = useUser();
  const router = useRouter();
  const [aor, setAor] = useState(defaultAor);
  const [category, setCategory] = useState<HuntingSourceCategory>("escort_listing");
  const [text, setText] = useState("");
  const [lawfulBasis, setLawfulBasis] = useState("");
  const [accessMethod, setAccessMethod] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [monitor, setMonitor] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  if (user?.role !== "admin") return null;

  function parseSites(): { url: string; name?: string }[] {
    return text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const parts = line.split("|").map((p) => p.trim());
        if (parts.length >= 2 && parts[0] && parts[1]) return { name: parts[0], url: parts[1] };
        return { url: parts[parts.length - 1] };
      })
      .filter((s) => s.url);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const sites = parseSites();
    if (sites.length === 0) {
      setError("Add at least one site (one per line).");
      return;
    }
    if (!lawfulBasis.trim() || !accessMethod.trim() || !jurisdiction.trim()) {
      setError("Lawful basis, access method, and jurisdiction are required to monitor.");
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    const res = await importHuntingSources({
      aor: aor.trim(),
      category,
      sites,
      authorization: {
        lawful_basis: lawfulBasis.trim(),
        access_method: accessMethod.trim(),
        jurisdiction: jurisdiction.trim(),
      },
      monitor,
    });
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setResult(
      `Imported ${res.data.imported} site(s) · ${res.data.monitored} now monitored · skipped ${res.data.skipped_existing} already known.`,
    );
    setText("");
    router.refresh();
  }

  const field = "rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm";

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="flex flex-wrap items-end gap-2">
        <div>
          <label htmlFor="import-aor" className="mb-1 block text-xs font-medium text-ink-muted">
            AOR
          </label>
          <input id="import-aor" value={aor} onChange={(e) => setAor(e.target.value)} className={`w-40 ${field}`} />
        </div>
        <div>
          <label htmlFor="import-category" className="mb-1 block text-xs font-medium text-ink-muted">
            Category
          </label>
          <select
            id="import-category"
            value={category}
            onChange={(e) => setCategory(e.target.value as HuntingSourceCategory)}
            className={field}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label htmlFor="import-sites" className="mb-1 block text-xs font-medium text-ink-muted">
          Sites <span className="text-ink-faint">(one per line — `Name | https://…` or a bare URL)</span>
        </label>
        <textarea
          id="import-sites"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          placeholder={"Backpage RI | https://example.invalid/ri\nhttps://another.invalid/listings"}
          className={`mono w-full ${field} text-xs`}
        />
      </div>

      <div className="rounded-md border border-surface-border bg-surface-sunken p-3">
        <div className="mb-2 text-xs font-medium text-ink-muted">
          Lawful basis <span className="text-ink-faint">(applied to every site — required to monitor)</span>
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <input
            aria-label="Lawful basis"
            value={lawfulBasis}
            onChange={(e) => setLawfulBasis(e.target.value)}
            placeholder="Lawful basis"
            className={field}
          />
          <input
            aria-label="Access method"
            value={accessMethod}
            onChange={(e) => setAccessMethod(e.target.value)}
            placeholder="Access method"
            className={field}
          />
          <input
            aria-label="Jurisdiction"
            value={jurisdiction}
            onChange={(e) => setJurisdiction(e.target.value)}
            placeholder="Jurisdiction"
            className={field}
          />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-1.5 text-xs text-ink-muted">
          <input type="checkbox" checked={monitor} onChange={(e) => setMonitor(e.target.checked)} />
          Start monitoring immediately
        </label>
        <button
          type="submit"
          disabled={busy || !text.trim()}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "Importing…" : monitor ? "Import & start monitoring" : "Import (authorize only)"}
        </button>
        {result && <span className="text-xs text-green-700">{result}</span>}
        {error && <span className="text-xs text-amber-700">{error}</span>}
      </div>
    </form>
  );
}
