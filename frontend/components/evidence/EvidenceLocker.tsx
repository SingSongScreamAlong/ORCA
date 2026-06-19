"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { EvidenceStatusBadge, Tag } from "@/components/ui/Badges";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { decideEvidence, verifyEvidence } from "@/lib/api";
import { formatTimestamp, humanize, shortId } from "@/lib/format";
import type { EvidenceDecision, EvidenceItem, EvidenceVerifyResult } from "@/lib/types";

const DECISIONS: { key: EvidenceDecision; label: string; cls: string }[] = [
  { key: "approve", label: "Approve", cls: "bg-green-50 text-green-700 ring-green-200" },
  { key: "needs_more_review", label: "Needs more", cls: "bg-sky-50 text-sky-700 ring-sky-200" },
  { key: "reject", label: "Reject", cls: "bg-surface text-ink-muted ring-surface-border" },
  { key: "quarantine", label: "Quarantine", cls: "bg-rose-50 text-rose-700 ring-rose-200" },
];

export function EvidenceLocker({
  items,
  sources,
  observations,
}: {
  items: EvidenceItem[];
  sources: Record<string, string>;
  observations: Record<string, string>;
}) {
  const router = useRouter();
  const [verifying, setVerifying] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, EvidenceVerifyResult>>({});
  const [busy, setBusy] = useState<string | null>(null);

  async function verify(id: string) {
    setVerifying(id);
    const res = await verifyEvidence(id);
    setVerifying(null);
    if (res.ok) setResults((r) => ({ ...r, [id]: res.data }));
  }

  async function decide(id: string, decision: EvidenceDecision) {
    setBusy(id);
    await decideEvidence(id, decision);
    setBusy(null);
    router.refresh();
  }

  if (items.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-surface-border px-4 py-10 text-center text-sm text-ink-faint">
        No evidence in this case yet. Use “Add evidence” to record an item.
      </div>
    );
  }

  return (
    <Table
      head={
        <>
          <Th>Evidence</Th>
          <Th>Type</Th>
          <Th>Source</Th>
          <Th>Status</Th>
          <Th>Integrity (SHA-256)</Th>
          <Th>Linked observation</Th>
          <Th>Actions</Th>
        </>
      }
    >
      {items.map((e) => {
        const result = results[e.id];
        return (
          <Tr key={e.id}>
            <Td>
              <div className="font-medium text-ink">{e.title}</div>
              <div className="mt-0.5 text-xs text-ink-faint">
                captured {e.captured_at ? formatTimestamp(e.captured_at) : "—"} · {e.access_method}
              </div>
              <div className="mt-1 flex flex-wrap gap-1">
                {e.legal_flags.requires_legal_review && <Tag>legal review</Tag>}
                {e.legal_flags.sensitive && <Tag>sensitive</Tag>}
                {e.legal_flags.partner_approved && <Tag>partner approved</Tag>}
              </div>
            </Td>
            <Td>
              <Tag>{humanize(e.evidence_type)}</Tag>
            </Td>
            <Td>{sources[e.source_id] ?? shortId(e.source_id)}</Td>
            <Td>
              <EvidenceStatusBadge status={e.status} />
            </Td>
            <Td>
              {e.sha256 ? (
                <div className="space-y-1">
                  <div className="mono text-xs text-ink-muted">{e.sha256.slice(0, 16)}…</div>
                  <button
                    type="button"
                    onClick={() => verify(e.id)}
                    disabled={verifying === e.id}
                    className="rounded border border-surface-border px-2 py-0.5 text-xs text-ink-muted hover:bg-surface-sunken disabled:opacity-50"
                  >
                    {verifying === e.id ? "Verifying…" : "Verify hash"}
                  </button>
                  {result && (
                    <div
                      className={`text-xs font-medium ${
                        result.verified === true
                          ? "text-band-confirmed"
                          : result.verified === false
                            ? "text-rose-700"
                            : "text-ink-faint"
                      }`}
                    >
                      {result.verified === true
                        ? "✓ verified"
                        : result.verified === false
                          ? "✗ mismatch"
                          : "— no stored bytes"}
                    </div>
                  )}
                </div>
              ) : (
                <span className="text-xs text-ink-faint">no hash</span>
              )}
            </Td>
            <Td>
              {e.observation_id ? (
                <span className="text-xs text-ink">{observations[e.observation_id] ?? shortId(e.observation_id)}</span>
              ) : (
                <span className="text-xs text-ink-faint">unlinked</span>
              )}
            </Td>
            <Td>
              <div className="flex flex-wrap gap-1">
                {DECISIONS.map((d) => (
                  <button
                    key={d.key}
                    type="button"
                    onClick={() => decide(e.id, d.key)}
                    disabled={busy === e.id}
                    className={`rounded px-2 py-0.5 text-xs font-medium ring-1 ring-inset disabled:opacity-50 ${d.cls}`}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </Td>
          </Tr>
        );
      })}
    </Table>
  );
}
