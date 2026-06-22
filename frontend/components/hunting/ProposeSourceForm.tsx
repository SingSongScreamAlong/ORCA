"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCan } from "@/components/auth/UserContext";
import { proposeHuntingSource } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { HuntingSourceCategory } from "@/lib/types";

const CATEGORIES: HuntingSourceCategory[] = [
  "escort_listing",
  "classified",
  "forum",
  "social",
  "aggregator",
  "other",
];

/**
 * Propose a candidate source. It enters the registry as `proposed` — never monitored — until
 * an administrator authorizes it with a lawful-basis record. Rendered only for operators who
 * can create material; the backend enforces the same.
 */
export function ProposeSourceForm({ defaultAor }: { defaultAor: string }) {
  const router = useRouter();
  const canPropose = useCan("create_observation");
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [category, setCategory] = useState<HuntingSourceCategory>("escort_listing");
  const [aor, setAor] = useState(defaultAor);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!canPropose) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const res = await proposeHuntingSource({
      name: name.trim(),
      url: url.trim(),
      category,
      aor: aor.trim(),
      discovery_notes: notes.trim() || undefined,
    });
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setName("");
    setUrl("");
    setNotes("");
    router.refresh();
  }

  return (
    <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
      <Field label="Name">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          placeholder="Venue label"
          className="rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
        />
      </Field>
      <Field label="URL / host">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          required
          placeholder="https://…"
          className="mono rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
        />
      </Field>
      <Field label="Category">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as HuntingSourceCategory)}
          className="rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {humanize(c)}
            </option>
          ))}
        </select>
      </Field>
      <Field label="AOR">
        <input
          value={aor}
          onChange={(e) => setAor(e.target.value)}
          required
          className="w-36 rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
        />
      </Field>
      <button
        type="submit"
        disabled={busy || !name.trim() || !url.trim()}
        className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
      >
        {busy ? "Proposing…" : "Propose source"}
      </button>
      {error && <span className="self-center text-xs text-amber-700">{error}</span>}
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-ink-muted">{label}</label>
      {children}
    </div>
  );
}
