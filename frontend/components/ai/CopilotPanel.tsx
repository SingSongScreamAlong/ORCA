"use client";

import { useState } from "react";
import { Tag } from "@/components/ui/Badges";
import { aiAssist, type AiAssistKind } from "@/lib/api";
import { formatTimestamp, humanize } from "@/lib/format";
import type { AiAssistResult } from "@/lib/types";

const ACTIONS: { kind: AiAssistKind; label: string; needs?: "note" | "section" | "draft" }[] = [
  { kind: "summarize", label: "Summarize approved material" },
  { kind: "extract-entities", label: "Extract candidate entities", needs: "note" },
  { kind: "suggest-relationships", label: "Suggest relationship candidates" },
  { kind: "draft-report-section", label: "Draft report section", needs: "section" },
  { kind: "check-citations", label: "Check citation gaps", needs: "draft" },
  { kind: "timeline-summary", label: "Generate timeline summary" },
];

/**
 * The Analyst Copilot. Every output is an AI *proposal* that requires human review — the
 * panel never writes case material. Hidden from anyone who cannot read case material
 * (partner export viewers never reach it; the backend enforces this regardless).
 */
export function CopilotPanel({ caseId }: { caseId: string }) {
  const [active, setActive] = useState<AiAssistKind | null>(null);
  const [busy, setBusy] = useState<AiAssistKind | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AiAssistResult | null>(null);
  const [note, setNote] = useState("");
  const [sectionTitle, setSectionTitle] = useState("Findings");
  const [draftText, setDraftText] = useState("");

  async function run(kind: AiAssistKind) {
    setBusy(kind);
    setError(null);
    const body =
      kind === "extract-entities"
        ? { note }
        : kind === "draft-report-section"
          ? { section_title: sectionTitle }
          : kind === "check-citations"
            ? { draft_text: draftText }
            : {};
    const res = await aiAssist(caseId, kind, body);
    setBusy(null);
    if (!res.ok) {
      setError(res.error);
      setResult(null);
      return;
    }
    setResult(res.data);
  }

  const activeNeeds = ACTIONS.find((a) => a.kind === active)?.needs;

  return (
    <div className="space-y-4">
      <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        <strong>AI suggestions are proposed only. Human review is required.</strong> The
        Copilot reasons over approved material only and never creates case material, approves
        anything, or appears in partner exports. Analysts decide.
      </div>

      <div className="flex flex-wrap gap-2">
        {ACTIONS.map((a) => (
          <button
            key={a.kind}
            type="button"
            onClick={() => {
              setActive(a.kind);
              if (!a.needs) run(a.kind);
            }}
            disabled={busy !== null}
            className="rounded-md border border-surface-border px-3 py-1.5 text-sm text-ink hover:bg-surface-sunken disabled:opacity-50"
          >
            {busy === a.kind ? "Working…" : a.label}
          </button>
        ))}
      </div>

      {activeNeeds === "note" && (
        <InlineInput
          label="Analyst note (optional — approved observations are used too)"
          value={note}
          onChange={setNote}
          onRun={() => run("extract-entities")}
          busy={busy !== null}
          textarea
        />
      )}
      {activeNeeds === "section" && (
        <InlineInput
          label="Report section title"
          value={sectionTitle}
          onChange={setSectionTitle}
          onRun={() => run("draft-report-section")}
          busy={busy !== null}
        />
      )}
      {activeNeeds === "draft" && (
        <InlineInput
          label="Draft text to check for citation gaps"
          value={draftText}
          onChange={setDraftText}
          onRun={() => run("check-citations")}
          busy={busy !== null}
          textarea
        />
      )}

      {error && <p className="text-sm text-amber-700">{error}</p>}

      {result && <CopilotResult result={result} onDismiss={() => setResult(null)} />}
    </div>
  );
}

function InlineInput({
  label, value, onChange, onRun, busy, textarea,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  onRun: () => void;
  busy: boolean;
  textarea?: boolean;
}) {
  return (
    <div className="space-y-2 rounded-md border border-surface-border p-3">
      <label className="block text-xs font-medium text-ink-muted">{label}</label>
      {textarea ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          className="w-full rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
        />
      ) : (
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
        />
      )}
      <button
        type="button"
        onClick={onRun}
        disabled={busy}
        className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
      >
        Run
      </button>
    </div>
  );
}

function CopilotResult({ result, onDismiss }: { result: AiAssistResult; onDismiss: () => void }) {
  return (
    <div className="space-y-3 rounded-md border border-surface-border p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Tag>{humanize(result.assist_type)}</Tag>
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
            proposed · requires human review
          </span>
        </div>
        <button type="button" onClick={onDismiss} className="text-xs text-ink-muted hover:text-ink">
          Dismiss
        </button>
      </div>

      {result.summary && <p className="whitespace-pre-wrap text-sm text-ink">{result.summary}</p>}

      {result.proposed_entities.length > 0 && (
        <Section title={`Candidate entities (${result.proposed_entities.length})`}>
          <ul className="space-y-1 text-sm">
            {result.proposed_entities.map((e, i) => (
              <li key={i} className="text-ink">
                <Tag>{humanize(e.entity_type)}</Tag> <span className="mono">{e.value}</span>{" "}
                <span className="text-ink-faint">— {e.rationale}</span>
                {e.possible_duplicate_of && (
                  <span className="ml-1 text-amber-700">(possible duplicate)</span>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {result.proposed_relationships.length > 0 && (
        <Section title={`Candidate relationships (${result.proposed_relationships.length})`}>
          <ul className="space-y-1 text-sm">
            {result.proposed_relationships.map((r, i) => (
              <li key={i} className="text-ink">
                <Tag>{humanize(r.relationship_type)}</Tag>{" "}
                <span className="mono">{r.source_value}</span> ↔{" "}
                <span className="mono">{r.target_value}</span>{" "}
                <span className="text-ink-faint">— {r.rationale}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {result.report_draft && (
        <Section title={`Draft: ${result.report_draft.section_title}`}>
          <pre className="overflow-x-auto whitespace-pre-wrap rounded-md bg-surface-sunken p-3 text-sm text-ink">
            {result.report_draft.draft_markdown}
          </pre>
          <button
            type="button"
            onClick={() => navigator.clipboard?.writeText(result.report_draft!.draft_markdown)}
            className="mt-2 rounded border border-surface-border px-2 py-0.5 text-xs text-ink-muted hover:bg-surface-sunken"
          >
            Copy draft
          </button>
        </Section>
      )}

      {result.unsupported_claims.length > 0 && (
        <Section title={`Unsupported claims (${result.unsupported_claims.length})`}>
          <ul className="list-disc space-y-1 pl-5 text-sm text-rose-700">
            {result.unsupported_claims.map((c, i) => (
              <li key={i}>
                {c.claim} <span className="text-ink-faint">— {c.reason}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {result.citation_gaps.length > 0 && (
        <Section title={`Citation gaps (${result.citation_gaps.length})`}>
          <ul className="list-disc space-y-1 pl-5 text-sm text-amber-700">
            {result.citation_gaps.map((g, i) => (
              <li key={i}>
                {g.location}: {g.claim}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {result.suggestions.length > 0 && (
        <Section title={`Notes (${result.suggestions.length})`}>
          <ul className="space-y-1 text-sm">
            {result.suggestions.map((s, i) => (
              <li key={i} className="text-ink">
                <Tag>{humanize(s.kind)}</Tag> {s.text}
              </li>
            ))}
          </ul>
        </Section>
      )}

      <div className="border-t border-surface-border pt-2 text-xs text-ink-faint">
        {result.meta.provider} · generated {formatTimestamp(result.meta.generated_at)} · status{" "}
        {result.meta.status} · {result.meta.source_material_ids.length} source item(s)
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-faint">{title}</div>
      {children}
    </div>
  );
}
