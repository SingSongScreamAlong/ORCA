"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createEvidence } from "@/lib/api";
import type { Case, EvidenceType, Observation, Source } from "@/lib/types";

const EVIDENCE_TYPES: EvidenceType[] = [
  "screenshot", "document", "image", "video", "web_archive", "analyst_note", "partner_file", "other",
];

export function EvidenceIntakeForm({
  cases,
  sources,
  observations,
  defaultCaseId,
}: {
  cases: Case[];
  sources: Source[];
  observations: Observation[];
  defaultCaseId?: string;
}) {
  const router = useRouter();
  const [caseId, setCaseId] = useState(defaultCaseId ?? cases[0]?.id ?? "");
  const [sourceId, setSourceId] = useState(sources[0]?.id ?? "");
  const [observationId, setObservationId] = useState("");
  const [title, setTitle] = useState("");
  const [evidenceType, setEvidenceType] = useState<EvidenceType>("screenshot");
  const [description, setDescription] = useState("");
  const [contentText, setContentText] = useState("");
  const [sha256, setSha256] = useState("");
  const [accessMethod, setAccessMethod] = useState("manual_upload");
  const [lawfulBasis, setLawfulBasis] = useState("publicly available information");
  const [requiresLegalReview, setRequiresLegalReview] = useState(false);
  const [sensitive, setSensitive] = useState(false);
  const [partnerApproved, setPartnerApproved] = useState(false);
  const [handlingNotes, setHandlingNotes] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const res = await createEvidence({
      case_id: caseId,
      source_id: sourceId,
      observation_id: observationId || undefined,
      title,
      description: description || undefined,
      evidence_type: evidenceType,
      content_text: contentText || undefined,
      sha256: sha256 || undefined,
      access_method: accessMethod,
      legal_flags: {
        lawful_basis: lawfulBasis || undefined,
        requires_legal_review: requiresLegalReview,
        sensitive,
        partner_approved: partnerApproved,
      },
      handling_notes: handlingNotes || undefined,
    });
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    router.push(`/cases/${caseId}?tab=evidence`);
    router.refresh();
  }

  const field = "w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm";
  const label = "mb-1 block text-xs font-medium text-ink-muted";

  return (
    <form onSubmit={submit} className="max-w-2xl space-y-6">
      {/* Safety warning — required acknowledgment */}
      <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
        <p className="font-semibold">Before adding evidence</p>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>Do not upload or store CSAM.</li>
          <li>Do not upload illegally obtained material.</li>
          <li>Do not store private/personal material unless authorized.</li>
          <li>Urgent or illegal content must be reported through authorized channels.</li>
        </ul>
        <p className="mt-2 text-xs">
          The Evidence Locker is for metadata, lawful files, and partner-approved workflows only.
        </p>
        <label className="mt-3 flex items-center gap-2 font-medium">
          <input type="checkbox" checked={acknowledged} onChange={(e) => setAcknowledged(e.target.checked)} />
          I confirm this item is lawful and permitted under the boundaries above.
        </label>
      </div>

      <div className="card space-y-4">
        <h2 className="text-sm font-semibold text-ink">Evidence item</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={label}>Case</label>
            <select className={field} value={caseId} onChange={(e) => setCaseId(e.target.value)} required>
              {cases.map((c) => (
                <option key={c.id} value={c.id}>{c.title}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={label}>Source</label>
            <select className={field} value={sourceId} onChange={(e) => setSourceId(e.target.value)} required>
              {sources.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={label}>Title</label>
            <input className={field} value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>
          <div>
            <label className={label}>Type</label>
            <select className={field} value={evidenceType} onChange={(e) => setEvidenceType(e.target.value as EvidenceType)}>
              {EVIDENCE_TYPES.map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label className={label}>Link to observation (optional, same case)</label>
          <select className={field} value={observationId} onChange={(e) => setObservationId(e.target.value)}>
            <option value="">— none —</option>
            {observations.map((o) => (
              <option key={o.id} value={o.id}>
                {(o.notes ?? o.id).slice(0, 60)} [{o.status}]
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={label}>Description</label>
          <textarea className={field} rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
      </div>

      <div className="card space-y-4">
        <h2 className="text-sm font-semibold text-ink">Integrity</h2>
        <div>
          <label className={label}>Text content to hash &amp; store (optional)</label>
          <textarea
            className={field}
            rows={3}
            value={contentText}
            onChange={(e) => setContentText(e.target.value)}
            placeholder="Paste lawful text content (e.g. an analyst note). ORCA computes and stores its SHA-256."
          />
        </div>
        <div>
          <label className={label}>Or a partner-provided SHA-256 (optional)</label>
          <input
            className={`${field} font-mono`}
            value={sha256}
            onChange={(e) => setSha256(e.target.value)}
            placeholder="64 hex characters"
          />
          <p className="mt-1 text-xs text-ink-faint">
            Provide content (which ORCA hashes) or a precomputed hash from a partner file. Without
            stored bytes, the hash is recorded but cannot be re-verified by ORCA.
          </p>
        </div>
        <div>
          <label className={label}>Access method</label>
          <input className={field} value={accessMethod} onChange={(e) => setAccessMethod(e.target.value)} />
        </div>
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
          Sensitive material
        </label>
        <label className="flex items-center gap-2 text-sm text-ink-muted">
          <input type="checkbox" checked={partnerApproved} onChange={(e) => setPartnerApproved(e.target.checked)} />
          Partner-approved
        </label>
        <div>
          <label className={label}>Handling notes</label>
          <input className={field} value={handlingNotes} onChange={(e) => setHandlingNotes(e.target.value)} />
        </div>
      </div>

      {error && <p className="text-sm text-amber-700">{error}</p>}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={busy || !acknowledged}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "Saving…" : "Add to evidence locker"}
        </button>
        <span className="text-xs text-ink-faint">Created as proposed; decide it in the locker.</span>
      </div>
    </form>
  );
}
