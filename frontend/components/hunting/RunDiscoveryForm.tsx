"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCan } from "@/components/auth/UserContext";
import { runHuntingDiscovery } from "@/lib/api";

/**
 * Run a discovery pass: paste candidate venues (one per line, `name | url`) and propose them
 * into the registry. They enter as `proposed` (discovery jobs) and are deduped by URL — an
 * administrator still authorizes each before anything is monitored. This is the manual seam a
 * licensed discovery connector would later drive; it performs no external fetch itself.
 */
export function RunDiscoveryForm({ defaultAor }: { defaultAor: string }) {
  const router = useRouter();
  const canRun = useCan("create_observation");
  const [aor, setAor] = useState(defaultAor);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ proposed: number; skipped: number } | null>(null);

  if (!canRun) return null;

  function parse(): { name: string; url: string }[] {
    return text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [name, url] = line.split("|").map((p) => p.trim());
        return { name: name || url, url: url || name };
      })
      .filter((c) => c.url);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const candidates = parse();
    if (candidates.length === 0) {
      setError("Add at least one candidate (name | url).");
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    const res = await runHuntingDiscovery({ aor: aor.trim(), candidates });
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setResult({ proposed: res.data.proposed.length, skipped: res.data.skipped_existing });
    setText("");
    router.refresh();
  }

  return (
    <form onSubmit={submit} className="space-y-2">
      <div className="flex items-end gap-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-muted">AOR</label>
          <input
            value={aor}
            onChange={(e) => setAor(e.target.value)}
            className="w-40 rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
          />
        </div>
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
        placeholder={"One per line:\nSite name | https://example.invalid"}
        className="mono w-full rounded-md border border-surface-border bg-surface px-2 py-1.5 text-xs"
      />
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={busy || !text.trim()}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "Running…" : "Run discovery"}
        </button>
        {result && (
          <span className="text-xs text-green-700">
            Proposed {result.proposed} · skipped {result.skipped} already known.
          </span>
        )}
        {error && <span className="text-xs text-amber-700">{error}</span>}
      </div>
    </form>
  );
}
