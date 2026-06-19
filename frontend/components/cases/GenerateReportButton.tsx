"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { generateReport } from "@/lib/api";

export function GenerateReportButton({ caseId }: { caseId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    const res = await generateReport(caseId);
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    router.refresh();
  }

  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        onClick={run}
        disabled={busy}
        className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
      >
        {busy ? "Generating…" : "Generate draft from approved evidence"}
      </button>
      {error && <span className="text-xs text-amber-700">{error}</span>}
    </div>
  );
}
