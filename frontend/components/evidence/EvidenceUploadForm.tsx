"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useCan } from "@/components/auth/UserContext";
import { uploadEvidence } from "@/lib/api";
import type { Source } from "@/lib/types";

/**
 * Manual evidence file upload (v0.7). Visible to users who may create evidence; the
 * backend additionally requires active, mutating membership in this case. A safety
 * acknowledgement is mandatory before the file is sent.
 */
export function EvidenceUploadForm({ caseId, sources }: { caseId: string; sources: Source[] }) {
  const router = useRouter();
  const canCreate = useCan("create_evidence");
  const fileRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [sourceId, setSourceId] = useState(sources[0]?.id ?? "");
  const [lawfulBasis, setLawfulBasis] = useState("publicly available information");
  const [requiresLegalReview, setRequiresLegalReview] = useState(false);
  const [sensitive, setSensitive] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  if (!canCreate) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setDone(null);
    const file = fileRef.current?.files?.[0];
    if (!file) return setError("Choose a file to upload.");
    if (!acknowledged) return setError("You must acknowledge the safety boundaries first.");
    if (!sourceId) return setError("Select a source.");

    const form = new FormData();
    form.append("file", file);
    form.append("source_id", sourceId);
    form.append("title", title || file.name);
    form.append("acknowledged", "true");
    form.append("lawful_basis", lawfulBasis);
    form.append("requires_legal_review", String(requiresLegalReview));
    form.append("sensitive", String(sensitive));

    setBusy(true);
    const res = await uploadEvidence(caseId, form);
    setBusy(false);
    if (!res.ok) return setError(res.error);
    setDone(
      res.data.status === "quarantined"
        ? `Uploaded and quarantined for review (${res.data.original_filename}).`
        : `Uploaded ${res.data.original_filename}.`,
    );
    setTitle("");
    setAcknowledged(false);
    if (fileRef.current) fileRef.current.value = "";
    router.refresh();
  }

  return (
    <form onSubmit={submit} className="space-y-3 rounded-md border border-surface-border p-4">
      <div className="text-sm font-medium text-ink">Upload a lawful file</div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-xs font-medium text-ink-muted">
          File
          <input
            ref={fileRef}
            type="file"
            className="mt-1 block w-full text-sm text-ink file:mr-3 file:rounded-md file:border-0 file:bg-surface-sunken file:px-3 file:py-1.5 file:text-sm"
          />
        </label>
        <label className="block text-xs font-medium text-ink-muted">
          Title
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Defaults to the filename"
            className="mt-1 block w-full rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
          />
        </label>
        <label className="block text-xs font-medium text-ink-muted">
          Source
          <select
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
            className="mt-1 block w-full rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
          >
            {sources.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-xs font-medium text-ink-muted">
          Lawful basis
          <input
            value={lawfulBasis}
            onChange={(e) => setLawfulBasis(e.target.value)}
            className="mt-1 block w-full rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
          />
        </label>
      </div>
      <div className="flex flex-wrap gap-4 text-xs text-ink-muted">
        <label className="flex items-center gap-1.5">
          <input type="checkbox" checked={requiresLegalReview} onChange={(e) => setRequiresLegalReview(e.target.checked)} />
          Requires legal review
        </label>
        <label className="flex items-center gap-1.5">
          <input type="checkbox" checked={sensitive} onChange={(e) => setSensitive(e.target.checked)} />
          Sensitive
        </label>
      </div>
      <div className="rounded-md bg-surface-sunken p-3 text-xs text-ink-muted">
        <label className="flex items-start gap-2">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
            className="mt-0.5"
          />
          <span>
            I confirm this file is lawful and authorised: no CSAM, no illegally obtained or
            unauthorised private material, and nothing for harassment, doxxing, stalking, or
            vigilante action. Urgent or illegal content is reported through authorised channels.
          </span>
        </label>
      </div>
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "Uploading…" : "Upload file"}
        </button>
        {error && <span className="text-xs text-amber-700">{error}</span>}
        {done && <span className="text-xs text-band-confirmed">{done}</span>}
      </div>
    </form>
  );
}
