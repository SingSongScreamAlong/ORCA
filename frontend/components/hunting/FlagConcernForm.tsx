"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCan } from "@/components/auth/UserContext";
import { raiseHuntingEscalation } from "@/lib/api";

/**
 * Flag a suspected-minor / CSAM concern from a monitored source. This is the charter's
 * **report-only, never-store** hard-stop: it records a minimal pointer and routes to the
 * escalation queue for a human to file an NCMEC CyberTipline report. **No material is stored** —
 * describe the concern only.
 */
export function FlagConcernForm({ sourceId, aor, url }: { sourceId: string; aor: string; url: string }) {
  const router = useRouter();
  const canFlag = useCan("create_observation");
  const [open, setOpen] = useState(false);
  const [concern, setConcern] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  if (!canFlag) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const res = await raiseHuntingEscalation({ aor, concern: concern.trim(), url, source_id: sourceId });
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setConcern("");
    setDone(true);
    setOpen(false);
    router.refresh();
  }

  if (!open) {
    return (
      <div>
        <button onClick={() => { setOpen(true); setDone(false); }} className="text-xs font-medium text-rose-700 hover:underline">
          ⚑ Flag suspected minor / CSAM
        </button>
        {done && <p className="mt-1 text-xs text-rose-700">Escalation raised — file an NCMEC CyberTipline report. No material was stored.</p>}
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-2 rounded-md border border-rose-200 bg-rose-50 p-3">
      <p className="text-xs font-medium text-rose-800">
        Report-only. Describe the concern — do NOT paste any illegal content. ORCA stores no
        material; a human files the NCMEC CyberTipline report.
      </p>
      <textarea
        value={concern}
        onChange={(e) => setConcern(e.target.value)}
        required
        rows={2}
        placeholder="Why you are flagging this (a pointer, not the content)…"
        className="w-full rounded-md border border-rose-200 bg-surface px-2 py-1.5 text-sm"
      />
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={busy || !concern.trim()}
          className="rounded-md bg-rose-700 px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "Raising…" : "Raise escalation"}
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
