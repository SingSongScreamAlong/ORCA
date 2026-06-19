"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createEntity, intakeObservation } from "@/lib/api";
import type { Case, EntityType, SourceReliability, SourceType } from "@/lib/types";

const ENTITY_TYPES: EntityType[] = [
  "phone_number", "alias", "account", "username", "location", "vehicle", "image",
  "advertisement", "tattoo_marker",
];
const SOURCE_TYPES: SourceType[] = ["website", "dataset", "manual_upload", "tip", "document"];
const RELIABILITIES: SourceReliability[] = ["unknown", "low", "medium", "high"];

interface EntityRow {
  entity_type: EntityType;
  value: string;
}

/**
 * Observation intake. Records a single observation with source metadata and
 * legal/handling flags. On submit it first resolves the referenced entities, then
 * intakes the observation — which enters the review queue as `proposed`.
 */
export function IntakeForm({ cases, defaultCaseId }: { cases: Case[]; defaultCaseId?: string }) {
  const router = useRouter();
  const [caseId, setCaseId] = useState(defaultCaseId ?? "");
  const [timestamp, setTimestamp] = useState(() => new Date().toISOString().slice(0, 16));
  const [sourceType, setSourceType] = useState<SourceType>("website");
  const [sourceName, setSourceName] = useState("");
  const [reliability, setReliability] = useState<SourceReliability>("medium");
  const [collector, setCollector] = useState("Development Analyst");
  const [notes, setNotes] = useState("");
  const [confidence, setConfidence] = useState(0.6);
  const [lawfulBasis, setLawfulBasis] = useState("publicly available information");
  const [requiresLegalReview, setRequiresLegalReview] = useState(false);
  const [sensitive, setSensitive] = useState(false);
  const [entities, setEntities] = useState<EntityRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateEntity(i: number, patch: Partial<EntityRow>) {
    setEntities((rows) => rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);

    // Resolve entities (create/dedup) to ids.
    const entityIds: string[] = [];
    for (const row of entities) {
      if (!row.value.trim()) continue;
      const res = await createEntity({ entity_type: row.entity_type, value: row.value.trim() });
      if (!res.ok) {
        setError(res.error);
        setBusy(false);
        return;
      }
      entityIds.push(res.data.id);
    }

    const res = await intakeObservation({
      case_id: caseId || undefined,
      timestamp: new Date(timestamp).toISOString(),
      source: { source_type: sourceType, name: sourceName || "Unnamed source", reliability },
      collector,
      notes: notes || undefined,
      confidence,
      entity_ids: entityIds,
      evidence_ids: [],
      handling: {
        lawful_basis: lawfulBasis || undefined,
        requires_legal_review: requiresLegalReview,
        sensitive,
      },
    });
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    // Land on the review queue — the observation is now awaiting a decision.
    router.push(caseId ? `/cases/${caseId}?tab=observations` : "/review");
    router.refresh();
  }

  const field = "w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm";
  const label = "mb-1 block text-xs font-medium text-ink-muted";

  return (
    <form onSubmit={submit} className="max-w-2xl space-y-6">
      <div className="card space-y-4">
        <h2 className="text-sm font-semibold text-ink">Observation</h2>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={label}>Case</label>
            <select className={field} value={caseId} onChange={(e) => setCaseId(e.target.value)}>
              <option value="">— none —</option>
              {cases.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={label}>Observed at</label>
            <input
              type="datetime-local"
              className={field}
              value={timestamp}
              onChange={(e) => setTimestamp(e.target.value)}
              required
            />
          </div>
        </div>

        <div>
          <label className={label}>Notes (what was observed)</label>
          <textarea
            className={field}
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="A single recorded fact."
          />
        </div>

        <div>
          <label className={label}>Confidence: {Math.round(confidence * 100)}%</label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={confidence}
            onChange={(e) => setConfidence(Number(e.target.value))}
            className="w-full"
          />
        </div>
      </div>

      <div className="card space-y-4">
        <h2 className="text-sm font-semibold text-ink">Source</h2>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className={label}>Type</label>
            <select className={field} value={sourceType} onChange={(e) => setSourceType(e.target.value as SourceType)}>
              {SOURCE_TYPES.map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
              ))}
            </select>
          </div>
          <div className="col-span-1">
            <label className={label}>Name</label>
            <input className={field} value={sourceName} onChange={(e) => setSourceName(e.target.value)} />
          </div>
          <div>
            <label className={label}>Reliability</label>
            <select className={field} value={reliability} onChange={(e) => setReliability(e.target.value as SourceReliability)}>
              {RELIABILITIES.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label className={label}>Collector</label>
          <input className={field} value={collector} onChange={(e) => setCollector(e.target.value)} />
        </div>
      </div>

      <div className="card space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink">Entities referenced</h2>
          <button
            type="button"
            className="text-sm font-medium text-accent"
            onClick={() => setEntities((r) => [...r, { entity_type: "phone_number", value: "" }])}
          >
            + Add entity
          </button>
        </div>
        {entities.length === 0 && (
          <p className="text-xs text-ink-faint">Optional. Add the entities this observation references.</p>
        )}
        {entities.map((row, i) => (
          <div key={i} className="flex items-center gap-2">
            <select
              className="rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
              value={row.entity_type}
              onChange={(e) => updateEntity(i, { entity_type: e.target.value as EntityType })}
            >
              {ENTITY_TYPES.map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
              ))}
            </select>
            <input
              className="flex-1 rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
              placeholder="value"
              value={row.value}
              onChange={(e) => updateEntity(i, { value: e.target.value })}
            />
            <button
              type="button"
              className="text-xs text-ink-faint hover:text-ink"
              onClick={() => setEntities((r) => r.filter((_, idx) => idx !== i))}
            >
              Remove
            </button>
          </div>
        ))}
      </div>

      <div className="card space-y-3">
        <h2 className="text-sm font-semibold text-ink">Legal &amp; handling</h2>
        <div>
          <label className={label}>Lawful basis</label>
          <input className={field} value={lawfulBasis} onChange={(e) => setLawfulBasis(e.target.value)} />
        </div>
        <label className="flex items-center gap-2 text-sm text-ink-muted">
          <input type="checkbox" checked={requiresLegalReview} onChange={(e) => setRequiresLegalReview(e.target.checked)} />
          Flag for legal review
        </label>
        <label className="flex items-center gap-2 text-sm text-ink-muted">
          <input type="checkbox" checked={sensitive} onChange={(e) => setSensitive(e.target.checked)} />
          Sensitive material (handle with care)
        </label>
        <p className="text-xs text-ink-faint">
          Do not record unlawfully obtained material. Report urgent or illegal material through
          authorized channels — see Safety &amp; Handling.
        </p>
      </div>

      {error && <p className="text-sm text-amber-700">{error}</p>}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "Submitting…" : "Submit for review"}
        </button>
        <span className="text-xs text-ink-faint">The observation enters the review queue as proposed.</span>
      </div>
    </form>
  );
}
