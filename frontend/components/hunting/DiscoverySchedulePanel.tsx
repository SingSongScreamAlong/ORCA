"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "@/components/auth/UserContext";
import {
  pauseHuntingSchedule,
  resumeHuntingSchedule,
  runHuntingScheduleNow,
} from "@/lib/api";
import type { HuntingDiscoveryScheduleStatus } from "@/lib/types";

/**
 * Continuous discovery — the autonomous cadence. Shows whether ORCA is seeking on its own, on
 * what interval, and the last run. Administrators get the runtime kill-switch (pause/resume)
 * and a "run now" trigger. Everything still only proposes; an admin authorizes each source.
 */
export function DiscoverySchedulePanel({ status }: { status: HuntingDiscoveryScheduleStatus | null }) {
  const user = useUser();
  const router = useRouter();
  const [busy, setBusy] = useState<null | "pause" | "resume" | "run">(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  if (!status) return null;
  const isAdmin = user?.role === "admin";

  async function act(which: "pause" | "resume" | "run") {
    setBusy(which);
    setError(null);
    setNote(null);
    const res =
      which === "pause"
        ? await pauseHuntingSchedule()
        : which === "resume"
          ? await resumeHuntingSchedule()
          : await runHuntingScheduleNow();
    setBusy(null);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    if (which === "run" && "total_proposed" in res.data) {
      setNote(
        `Swept ${res.data.aors.length} AOR(s) — proposed ${res.data.total_proposed} · skipped ${res.data.total_skipped} already known.`,
      );
    }
    router.refresh();
  }

  return (
    <div className="space-y-3">
      <CadenceState status={status} />

      {isAdmin && (
        <div className="flex flex-wrap items-center gap-2">
          {status.paused ? (
            <Btn onClick={() => act("resume")} kind="primary" disabled={busy !== null}>
              {busy === "resume" ? "Resuming…" : "Resume cadence"}
            </Btn>
          ) : (
            <Btn onClick={() => act("pause")} disabled={busy !== null}>
              {busy === "pause" ? "Pausing…" : "Pause cadence (kill-switch)"}
            </Btn>
          )}
          <Btn onClick={() => act("run")} kind="primary" disabled={busy !== null}>
            {busy === "run" ? "Running…" : "Run now"}
          </Btn>
        </div>
      )}

      {note && <p className="text-xs text-green-700">{note}</p>}
      {error && <p className="text-xs text-amber-700">{error}</p>}
    </div>
  );
}

function CadenceState({ status }: { status: HuntingDiscoveryScheduleStatus }) {
  const tone = status.paused
    ? "border-amber-200 bg-amber-50 text-amber-800"
    : status.enabled
      ? "border-green-200 bg-green-50 text-green-800"
      : "border-surface-border bg-surface-sunken text-ink-muted";
  const state = !status.enabled
    ? "off"
    : status.paused
      ? "paused (kill-switch engaged)"
      : status.running
        ? "running"
        : "enabled";
  return (
    <div className={`rounded-md border px-3 py-2 text-xs ${tone}`}>
      <p>
        Cadence is <span className="font-medium">{state}</span> · every{" "}
        <span className="font-medium">{status.interval_minutes} min</span> · up to{" "}
        {status.limit_per_aor} candidates per AOR.
      </p>
      <p className="mt-0.5">
        {status.runs > 0 ? (
          <>
            {status.runs} run(s) ·{" "}
            {status.last_error ? (
              <span className="text-amber-700">last error: {status.last_error}</span>
            ) : (
              <>
                last proposed {status.last_total_proposed ?? 0} · skipped{" "}
                {status.last_total_skipped ?? 0}
                {status.last_aors.length ? ` across ${status.last_aors.join(", ")}` : ""}
              </>
            )}
          </>
        ) : (
          "No runs yet."
        )}
      </p>
    </div>
  );
}

function Btn({
  children,
  onClick,
  kind = "default",
  disabled,
}: {
  children: React.ReactNode;
  onClick: () => void;
  kind?: "primary" | "default";
  disabled?: boolean;
}) {
  const cls =
    kind === "primary"
      ? "bg-accent text-white hover:opacity-90"
      : "border border-surface-border text-ink-muted hover:bg-surface-sunken hover:text-ink";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`rounded-md px-3 py-1.5 text-sm font-medium disabled:opacity-50 ${cls}`}
    >
      {children}
    </button>
  );
}
