"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  closeHuntingEscalation,
  dismissHuntingEscalation,
  reportHuntingEscalation,
} from "@/lib/api";
import type { ApiResult } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { HuntingEscalation } from "@/lib/types";

const STATUS_STYLE: Record<string, string> = {
  open: "bg-rose-50 text-rose-700 ring-rose-200",
  reported: "bg-amber-50 text-amber-700 ring-amber-200",
  closed: "bg-slate-100 text-slate-500 ring-slate-200",
  dismissed: "bg-slate-100 text-slate-500 ring-slate-200",
};

/**
 * Admin queue for suspected-minor/CSAM escalations. Each is a *pointer*, never the material.
 * The workflow is: record an NCMEC CyberTipline reference once filed → close; or dismiss if it
 * turns out not to be CSAM. ORCA does not transmit to NCMEC — a human files; this tracks it.
 */
export function EscalationsPanel({ escalations }: { escalations: HuntingEscalation[] }) {
  if (escalations.length === 0) {
    return <p className="text-sm text-ink-faint">No escalations.</p>;
  }
  return (
    <div className="space-y-3">
      {escalations.map((e) => (
        <Row key={e.id} esc={e} />
      ))}
    </div>
  );
}

function Row({ esc }: { esc: HuntingEscalation }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ref, setRef] = useState("");

  async function run(call: Promise<ApiResult<HuntingEscalation>>) {
    setBusy(true);
    setError(null);
    const res = await call;
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    router.refresh();
  }

  return (
    <div className="rounded-md border border-surface-border bg-surface-sunken p-3">
      <div className="flex items-center gap-2">
        <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${STATUS_STYLE[esc.status]}`}>
          {humanize(esc.status)}
        </span>
        <span className="text-xs text-ink-faint">
          {esc.aor} · raised by {esc.raised_by} · {new Date(esc.raised_at).toLocaleString()}
        </span>
      </div>
      <p className="mt-1 text-sm text-ink">{esc.concern}</p>
      {esc.url && <p className="mono mt-0.5 text-xs text-ink-faint">{esc.url}</p>}
      {esc.ncmec_reference && (
        <p className="mt-0.5 text-xs text-ink-muted">NCMEC reference: {esc.ncmec_reference}</p>
      )}

      {esc.status === "open" && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <input
            value={ref}
            onChange={(e) => setRef(e.target.value)}
            placeholder="NCMEC CyberTipline ref"
            className="mono rounded-md border border-surface-border bg-surface px-2 py-1 text-xs"
          />
          <button
            disabled={busy || !ref.trim()}
            onClick={() => run(reportHuntingEscalation(esc.id, ref.trim()))}
            className="rounded-md bg-accent px-2.5 py-1 text-xs font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            Mark reported
          </button>
          <button
            disabled={busy}
            onClick={() => run(dismissHuntingEscalation(esc.id, "Reviewed — not CSAM."))}
            className="rounded-md border border-surface-border px-2.5 py-1 text-xs font-medium text-ink-muted hover:bg-surface"
          >
            Dismiss
          </button>
        </div>
      )}
      {esc.status === "reported" && (
        <button
          disabled={busy}
          onClick={() => run(closeHuntingEscalation(esc.id, "Filed; nothing further."))}
          className="mt-2 rounded-md border border-surface-border px-2.5 py-1 text-xs font-medium text-ink-muted hover:bg-surface"
        >
          Close
        </button>
      )}
      {error && <p className="mt-1 text-xs text-amber-700">{error}</p>}
    </div>
  );
}
