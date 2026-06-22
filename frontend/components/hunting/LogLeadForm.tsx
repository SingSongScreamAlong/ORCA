"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCan } from "@/components/auth/UserContext";
import { ingestHuntingLead } from "@/lib/api";
import { humanize } from "@/lib/format";

const ENTITY_TYPES = [
  "phone_number",
  "alias",
  "account",
  "username",
  "location",
  "vehicle",
  "image",
  "advertisement",
  "tattoo_marker",
];

/**
 * Log a **text-only** lead from a monitored source. It becomes a *proposed observation* in the
 * review queue — never auto-approved. No media is collected here (CSAM-safe by construction).
 * Shown to operators who can create observations; the backend enforces the same and that the
 * source is actually monitored.
 */
export function LogLeadForm({ sourceId }: { sourceId: string }) {
  const router = useRouter();
  const canLog = useCan("create_observation");
  const [open, setOpen] = useState(false);
  const [summary, setSummary] = useState("");
  const [entType, setEntType] = useState("phone_number");
  const [entValue, setEntValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  if (!canLog) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const entities = entValue.trim()
      ? [{ entity_type: entType, value: entValue.trim() }]
      : [];
    const res = await ingestHuntingLead(sourceId, { summary: summary.trim(), entities });
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setSummary("");
    setEntValue("");
    setDone(true);
    setOpen(false);
    router.refresh();
  }

  if (!open) {
    return (
      <div className="space-y-1">
        <button
          onClick={() => {
            setOpen(true);
            setDone(false);
          }}
          className="text-xs font-medium text-accent hover:underline"
        >
          + Log a lead
        </button>
        {done && <p className="text-xs text-green-700">Lead sent to the review queue.</p>}
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-2 rounded-md border border-surface-border bg-surface-sunken p-3">
      <p className="text-xs text-ink-faint">
        Text only — no media. Becomes a proposed observation for an analyst to review.
      </p>
      <textarea
        value={summary}
        onChange={(e) => setSummary(e.target.value)}
        required
        rows={2}
        placeholder="What was observed (text summary)…"
        className="w-full rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
      />
      <div className="flex flex-wrap items-end gap-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-muted">Entity (optional)</label>
          <select
            value={entType}
            onChange={(e) => setEntType(e.target.value)}
            className="rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
          >
            {ENTITY_TYPES.map((t) => (
              <option key={t} value={t}>
                {humanize(t)}
              </option>
            ))}
          </select>
        </div>
        <input
          value={entValue}
          onChange={(e) => setEntValue(e.target.value)}
          placeholder="value (e.g. +1…)"
          className="mono rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
        />
        <button
          type="submit"
          disabled={busy || !summary.trim()}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "Sending…" : "Send to review"}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded-md border border-surface-border px-3 py-1.5 text-sm font-medium text-ink-muted hover:bg-surface"
        >
          Cancel
        </button>
      </div>
      {error && <p className="text-xs text-amber-700">{error}</p>}
    </form>
  );
}
