"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCan } from "@/components/auth/UserContext";
import { runAutoDiscovery, runAutoDiscoverySweep } from "@/lib/api";
import type { HuntingDiscoveryStatus } from "@/lib/types";

/**
 * Autonomous discovery — ORCA *seeks* new venues in an AOR through the configured lawful source,
 * so the operator need not trawl. It only ever **proposes**: every candidate enters the registry
 * as `proposed` (deduped by URL) and an administrator still authorizes each, with a recorded
 * lawful basis, before anything is monitored. Disabled by default — the panel says so plainly and
 * the button reaches out only when a provider is configured. No scraping, no dark-web.
 */
export function AutoDiscoveryPanel({
  defaultAor,
  status,
}: {
  defaultAor: string;
  status: HuntingDiscoveryStatus | null;
}) {
  const router = useRouter();
  const canRun = useCan("create_observation");
  const [aor, setAor] = useState(defaultAor);
  const [limit, setLimit] = useState(10);
  const [busy, setBusy] = useState<null | "one" | "sweep">(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  if (!canRun) return null;

  const enabled = status?.enabled ?? false;
  const watchlist = status?.aors ?? [];

  async function seekOne(e: React.FormEvent) {
    e.preventDefault();
    setBusy("one");
    setError(null);
    setResult(null);
    const res = await runAutoDiscovery(aor.trim(), limit);
    setBusy(null);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setResult(
      `Sought ${res.data.aor} via ${res.data.provider ?? "provider"} — proposed ${res.data.proposed.length} · skipped ${res.data.skipped_existing} already known.`,
    );
    router.refresh();
  }

  async function sweep() {
    setBusy("sweep");
    setError(null);
    setResult(null);
    const res = await runAutoDiscoverySweep(undefined, limit);
    setBusy(null);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setResult(
      `Swept ${res.data.aors.length} AOR(s) via ${res.data.provider ?? "provider"} — proposed ${res.data.total_proposed} · skipped ${res.data.total_skipped} already known.`,
    );
    router.refresh();
  }

  return (
    <form onSubmit={seekOne} className="space-y-3">
      <ProviderState status={status} />

      <div className="flex flex-wrap items-end gap-2">
        <div>
          <label htmlFor="auto-discovery-aor" className="mb-1 block text-xs font-medium text-ink-muted">
            AOR
          </label>
          <input
            id="auto-discovery-aor"
            value={aor}
            onChange={(e) => setAor(e.target.value)}
            className="w-44 rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
          />
        </div>
        <div>
          <label
            htmlFor="auto-discovery-max"
            className="mb-1 block text-xs font-medium text-ink-muted"
          >
            Max candidates
          </label>
          <input
            id="auto-discovery-max"
            type="number"
            min={1}
            max={50}
            value={limit}
            onChange={(e) => setLimit(Math.max(1, Math.min(50, Number(e.target.value) || 1)))}
            className="w-24 rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={busy !== null || !aor.trim() || !enabled}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {busy === "one" ? "Seeking…" : "Run autonomous discovery"}
        </button>
        <button
          type="button"
          onClick={sweep}
          disabled={busy !== null || !enabled || watchlist.length === 0}
          title={watchlist.length === 0 ? "Add an AOR to the watchlist to enable the sweep." : undefined}
          className="rounded-md border border-accent px-3 py-1.5 text-sm font-medium text-accent hover:bg-accent-soft disabled:opacity-50"
        >
          {busy === "sweep" ? "Sweeping…" : `Sweep watchlist (${watchlist.length})`}
        </button>
      </div>

      {result && (
        <p className="text-xs text-green-700">
          {result} Each still needs authorization before monitoring.
        </p>
      )}
      {error && <p className="text-xs text-amber-700">{error}</p>}
    </form>
  );
}

function ProviderState({ status }: { status: HuntingDiscoveryStatus | null }) {
  if (!status || status.provider === "disabled") {
    return (
      <p className="rounded-md border border-surface-border bg-surface-sunken px-3 py-2 text-xs text-ink-muted">
        Autonomous discovery is <span className="font-medium">disabled</span>. It turns on only when
        a licensed source is configured (<code className="mono">ORCA_HUNTING_DISCOVERY_PROVIDER</code>)
        with a recorded lawful basis — see{" "}
        <a
          className="text-accent hover:underline"
          href="https://github.com/SingSongScreamAlong/ORCA/blob/main/docs/hunting_grounds_discovery.md"
        >
          the discovery guide
        </a>
        . Use the manual discovery card meanwhile.
      </p>
    );
  }
  const tone = status.configured
    ? "border-green-200 bg-green-50 text-green-800"
    : "border-amber-200 bg-amber-50 text-amber-800";
  return (
    <p className={`rounded-md border px-3 py-2 text-xs ${tone}`}>
      Provider <span className="mono font-medium">{status.provider}</span>
      {status.host ? (
        <>
          {" "}
          · <span className="mono">{status.host}</span>
        </>
      ) : null}{" "}
      · lawful basis {status.lawful_basis_recorded ? "recorded" : "not recorded"}
      {status.tor_enabled ? " · via Tor (dark web)" : ""}
      {status.configured ? "" : " · not fully configured"}. Discovered venues enter as proposals only.
    </p>
  );
}
