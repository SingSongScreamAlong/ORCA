"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCan } from "@/components/auth/UserContext";
import { generateReport, publishReport } from "@/lib/api";

/**
 * Role-aware report actions: generate a draft (generate_report) and publish a draft as
 * an approved package (publish_report). Buttons appear only for permitted roles.
 */
export function GenerateReportButton({
  caseId,
  latestReportId,
  latestStatus,
}: {
  caseId: string;
  latestReportId?: string;
  latestStatus?: string;
}) {
  const router = useRouter();
  const canGenerate = useCan("generate_report");
  const canPublish = useCan("publish_report");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(label: string, fn: () => Promise<{ ok: boolean; error?: string }>) {
    setBusy(label);
    setError(null);
    const res = await fn();
    setBusy(null);
    if (!res.ok) {
      setError(res.error ?? "Failed.");
      return;
    }
    router.refresh();
  }

  if (!canGenerate && !canPublish) {
    return <span className="text-xs text-ink-faint">Report authoring requires an analyst role.</span>;
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-2">
        {canGenerate && (
          <button
            type="button"
            onClick={() => run("gen", () => generateReport(caseId))}
            disabled={busy !== null}
            className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {busy === "gen" ? "Generating…" : "Generate draft"}
          </button>
        )}
        {canPublish && latestReportId && latestStatus !== "final" && (
          <button
            type="button"
            onClick={() => run("pub", () => publishReport(latestReportId))}
            disabled={busy !== null}
            className="rounded-md px-3 py-1.5 text-sm font-medium text-green-700 ring-1 ring-inset ring-green-200 hover:bg-green-50 disabled:opacity-50"
          >
            {busy === "pub" ? "Publishing…" : "Publish (approve package)"}
          </button>
        )}
      </div>
      {error && <span className="text-xs text-amber-700">{error}</span>}
    </div>
  );
}
