"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "@/components/auth/UserContext";
import { addHuntingWatchlist, removeHuntingWatchlist } from "@/lib/api";
import type { HuntingWatchlistEntry } from "@/lib/types";

/**
 * Operator-managed AOR watchlist — the areas the autonomous cadence sweeps for new venues.
 * Administrators add/remove AORs here (no redeploy); everyone sees the current list. The
 * persisted watchlist takes precedence over the env fallback.
 */
export function WatchlistEditor({ entries }: { entries: HuntingWatchlistEntry[] }) {
  const user = useUser();
  const router = useRouter();
  const isAdmin = user?.role === "admin";
  const [aor, setAor] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    const value = aor.trim();
    if (!value) return;
    setBusy(true);
    setError(null);
    const res = await addHuntingWatchlist(value);
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setAor("");
    router.refresh();
  }

  async function remove(value: string) {
    setBusy(true);
    setError(null);
    const res = await removeHuntingWatchlist(value);
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    router.refresh();
  }

  return (
    <div className="space-y-2">
      <div className="text-xs font-medium text-ink-muted">
        Watchlist <span className="text-ink-faint">(areas the cadence sweeps)</span>
      </div>
      {entries.length === 0 ? (
        <p className="text-xs text-ink-faint">
          No AORs on the watchlist{isAdmin ? " — add one below." : " (the env fallback applies)."}
        </p>
      ) : (
        <ul className="flex flex-wrap gap-1.5">
          {entries.map((e) => (
            <li
              key={e.aor}
              className="inline-flex items-center gap-1.5 rounded-md border border-surface-border bg-surface px-2 py-1 text-xs"
              title={`Added by ${e.added_by}`}
            >
              <span className="text-ink">{e.aor}</span>
              {isAdmin && (
                <button
                  type="button"
                  onClick={() => remove(e.aor)}
                  disabled={busy}
                  className="text-ink-faint hover:text-rose-600 disabled:opacity-50"
                  aria-label={`Remove ${e.aor} from the watchlist`}
                >
                  ×
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {isAdmin && (
        <form onSubmit={add} className="flex items-center gap-2">
          <input
            value={aor}
            onChange={(ev) => setAor(ev.target.value)}
            placeholder="Add an AOR…"
            aria-label="Add an AOR to the watchlist"
            className="w-44 rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
          />
          <button
            type="submit"
            disabled={busy || !aor.trim()}
            className="rounded-md border border-surface-border px-3 py-1.5 text-sm font-medium text-ink-muted hover:bg-surface-sunken hover:text-ink disabled:opacity-50"
          >
            Add
          </button>
        </form>
      )}
      {error && <p className="text-xs text-amber-700">{error}</p>}
    </div>
  );
}
