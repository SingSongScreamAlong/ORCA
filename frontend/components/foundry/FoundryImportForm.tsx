"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { foundryImport } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { FoundryImportResult } from "@/lib/types";

// ORCA's fixed entity-type vocabulary (must match the backend EntityType enum).
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
 * Import objects of one Foundry object type into ORCA as entities. Admin-only (the backend
 * enforces it); read-only against Foundry — only ORCA's deduplicated entity store is written,
 * so re-importing is idempotent. The analyst picks which Foundry property becomes the entity
 * value and the ORCA entity type.
 */
export function FoundryImportForm({ objectType }: { objectType: string }) {
  const router = useRouter();
  const [entityType, setEntityType] = useState("username");
  const [valueProperty, setValueProperty] = useState("");
  const [limit, setLimit] = useState(10);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<FoundryImportResult | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setResult(null);
    const res = await foundryImport({
      object_type: objectType,
      entity_type: entityType,
      value_property: valueProperty.trim(),
      limit,
    });
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setResult(res.data);
    router.refresh(); // so /entities reflects the new records
  }

  return (
    <div className="space-y-3">
      <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-muted">Property → value</label>
          <input
            value={valueProperty}
            onChange={(ev) => setValueProperty(ev.target.value)}
            required
            placeholder="e.g. tailNum"
            className="mono rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-muted">ORCA entity type</label>
          <select
            value={entityType}
            onChange={(ev) => setEntityType(ev.target.value)}
            className="rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
          >
            {ENTITY_TYPES.map((t) => (
              <option key={t} value={t}>
                {humanize(t)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-muted">Limit</label>
          <input
            type="number"
            min={1}
            max={50}
            value={limit}
            onChange={(ev) => setLimit(Number(ev.target.value))}
            className="w-20 rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={busy || !valueProperty.trim()}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "Importing…" : "Import to ORCA"}
        </button>
        {error && <span className="self-center text-xs text-amber-700">{error}</span>}
      </form>

      {result && (
        <div className="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
          Read <strong>{result.read}</strong> · created <strong>{result.created}</strong> ·
          already present <strong>{result.resolved_existing}</strong> · skipped{" "}
          <strong>{result.skipped}</strong>. Imported entities are now in{" "}
          <a href="/entities" className="underline">
            Entities
          </a>
          .
        </div>
      )}
    </div>
  );
}
