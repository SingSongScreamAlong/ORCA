"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Tag } from "@/components/ui/Badges";
import { generateReportPackage, getPackageArtifact } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import type { ReportPackageSummary } from "@/lib/types";

const ARTIFACTS: { kind: "report" | "manifest" | "package"; label: string; ext: string }[] = [
  { kind: "report", label: "Report (.md)", ext: "md" },
  { kind: "manifest", label: "Manifest (.json)", ext: "json" },
  { kind: "package", label: "Package (.zip)", ext: "zip" },
];

/**
 * Report package list with download actions, and (for authorised roles on a case) a
 * Generate action. Partner export viewers see the same view, read-only — the backend
 * scopes packages to assigned cases and never exposes raw evidence here.
 */
export function ReportPackages({
  packages,
  caseId,
  canGenerate,
}: {
  packages: ReportPackageSummary[];
  caseId?: string;
  canGenerate?: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  async function generate() {
    if (!caseId) return;
    setBusy(true);
    setError(null);
    const res = await generateReportPackage(caseId);
    setBusy(false);
    if (!res.ok) return setError(res.error);
    router.refresh();
  }

  async function download(id: string, kind: "report" | "manifest" | "package", ext: string) {
    const key = `${id}:${kind}`;
    setDownloading(key);
    setError(null);
    const res = await getPackageArtifact(id, kind);
    setDownloading(null);
    if (!res.ok) return setError(res.error);
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = kind === "package" ? `report-package-${id}.zip` : `${kind}-${id}.${ext}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      {caseId && canGenerate && (
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={generate}
            disabled={busy}
            className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {busy ? "Generating…" : "Generate report package"}
          </button>
          <span className="text-xs text-ink-faint">
            Builds an immutable, partner-ready snapshot from approved material only.
          </span>
        </div>
      )}
      {error && <p className="text-xs text-amber-700">{error}</p>}

      {packages.length === 0 ? (
        <div className="rounded-md border border-dashed border-surface-border px-4 py-10 text-center text-sm text-ink-faint">
          No report packages yet.
        </div>
      ) : (
        <ul className="space-y-3">
          {packages.map((p) => (
            <li key={p.id} className="rounded-md border border-surface-border p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-ink">{p.title}</span>
                <Tag>{p.status}</Tag>
                <Tag>handling: {p.handling_level}</Tag>
              </div>
              <div className="mt-1 text-xs text-ink-faint">
                generated {formatTimestamp(p.created_at)} by {p.generated_by} ·{" "}
                {p.counts.approved_observations} obs · {p.counts.approved_relationships} rel ·{" "}
                {p.counts.cited_evidence} evidence
              </div>
              <div className="mono mt-1 text-xs text-ink-faint">
                report {p.report_sha256.slice(0, 12)}… · manifest {p.manifest_sha256.slice(0, 12)}…
              </div>
              <ul className="mt-2 list-disc pl-5 text-xs text-ink-muted">
                {p.caveats.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
              <div className="mt-2 flex flex-wrap gap-2">
                {ARTIFACTS.map((a) => (
                  <button
                    key={a.kind}
                    type="button"
                    onClick={() => download(p.id, a.kind, a.ext)}
                    disabled={downloading === `${p.id}:${a.kind}`}
                    className="rounded border border-surface-border px-2 py-0.5 text-xs text-ink-muted hover:bg-surface-sunken disabled:opacity-50"
                  >
                    {downloading === `${p.id}:${a.kind}` ? "Preparing…" : `Download ${a.label}`}
                  </button>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
