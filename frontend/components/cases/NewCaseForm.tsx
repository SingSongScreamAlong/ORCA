"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCan } from "@/components/auth/UserContext";
import { createCase } from "@/lib/api";

export function NewCaseForm() {
  const router = useRouter();
  const canCreate = useCan("create_case");
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [owner, setOwner] = useState("Development Analyst");
  const [summary, setSummary] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!canCreate) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const res = await createCase({ title, owner, summary: summary || undefined });
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    router.push(`/cases/${res.data.id}`);
    router.refresh();
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
      >
        New case
      </button>
    );
  }

  const field = "w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm";

  return (
    <form onSubmit={submit} className="card w-full max-w-xl space-y-3">
      <h2 className="text-sm font-semibold text-ink">New case</h2>
      <input className={field} placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
      <input className={field} placeholder="Owner" value={owner} onChange={(e) => setOwner(e.target.value)} required />
      <textarea
        className={field}
        rows={2}
        placeholder="Summary (optional)"
        value={summary}
        onChange={(e) => setSummary(e.target.value)}
      />
      {error && <p className="text-sm text-amber-700">{error}</p>}
      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "Creating…" : "Create"}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded-md px-3 py-1.5 text-sm text-ink-muted hover:bg-surface-sunken"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
