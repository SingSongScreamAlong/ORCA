"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "@/components/auth/UserContext";
import {
  authorizeHuntingSource,
  monitorHuntingSource,
  rejectHuntingSource,
  retireHuntingSource,
  suspendHuntingSource,
} from "@/lib/api";
import type { ApiResult } from "@/lib/api";
import type { HuntingSource } from "@/lib/types";

type Panel = "authorize" | "reject" | "suspend" | "retire";

/**
 * Admin-only lifecycle controls for a Hunting Grounds source. The actions shown depend on the
 * source's status; the **authorize** action requires a complete lawful-basis record, mirroring
 * the backend gate. Rendered for administrators only (the backend enforces it regardless).
 */
export function SourceControls({ source }: { source: HuntingSource }) {
  const user = useUser();
  const router = useRouter();
  const [panel, setPanel] = useState<Panel | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!user || user.role !== "admin") return null;
  if (source.status === "retired" || source.status === "rejected") return null;

  async function run(call: Promise<ApiResult<HuntingSource>>) {
    setBusy(true);
    setError(null);
    const res = await call;
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setPanel(null);
    router.refresh();
  }

  const id = source.id;
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {source.status === "proposed" && (
          <>
            <Btn onClick={() => setPanel(panel === "authorize" ? null : "authorize")} kind="primary">
              Authorize…
            </Btn>
            <Btn onClick={() => setPanel(panel === "reject" ? null : "reject")}>Reject…</Btn>
          </>
        )}
        {source.status === "authorized" && (
          <Btn onClick={() => run(monitorHuntingSource(id))} kind="primary" disabled={busy}>
            Begin monitoring
          </Btn>
        )}
        {source.status === "suspended" && (
          <Btn onClick={() => run(monitorHuntingSource(id))} kind="primary" disabled={busy}>
            Resume monitoring
          </Btn>
        )}
        {(source.status === "authorized" || source.status === "monitored") && (
          <Btn onClick={() => setPanel(panel === "suspend" ? null : "suspend")} disabled={busy}>
            Suspend…
          </Btn>
        )}
        {source.status !== "proposed" && (
          <Btn onClick={() => setPanel(panel === "retire" ? null : "retire")} disabled={busy}>
            Retire…
          </Btn>
        )}
      </div>

      {panel === "authorize" && (
        <AuthorizeForm busy={busy} onCancel={() => setPanel(null)} onSubmit={(b) => run(authorizeHuntingSource(id, b))} />
      )}
      {panel === "reject" && (
        <ReasonForm label="Reason for rejecting" busy={busy} onCancel={() => setPanel(null)} onSubmit={(r) => run(rejectHuntingSource(id, r))} />
      )}
      {panel === "suspend" && (
        <ReasonForm label="Reason for suspending" busy={busy} onCancel={() => setPanel(null)} onSubmit={(r) => run(suspendHuntingSource(id, r))} />
      )}
      {panel === "retire" && (
        <ReasonForm label="Reason for retiring" busy={busy} onCancel={() => setPanel(null)} onSubmit={(r) => run(retireHuntingSource(id, r))} />
      )}

      {error && <p className="text-xs text-amber-700">{error}</p>}
    </div>
  );
}

function AuthorizeForm({
  busy,
  onSubmit,
  onCancel,
}: {
  busy: boolean;
  onSubmit: (b: { lawful_basis: string; access_method: string; jurisdiction: string; legal_review_note?: string }) => void;
  onCancel: () => void;
}) {
  const [lawfulBasis, setLawfulBasis] = useState("");
  const [accessMethod, setAccessMethod] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [note, setNote] = useState("");
  const ready = lawfulBasis.trim() && accessMethod.trim() && jurisdiction.trim();
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          lawful_basis: lawfulBasis.trim(),
          access_method: accessMethod.trim(),
          jurisdiction: jurisdiction.trim(),
          legal_review_note: note.trim() || undefined,
        });
      }}
      className="space-y-2 rounded-md border border-surface-border bg-surface-sunken p-3"
    >
      <p className="text-xs text-ink-faint">
        Authorization requires a recorded lawful basis. The source is monitored only after this.
      </p>
      <Input label="Lawful basis" value={lawfulBasis} onChange={setLawfulBasis} placeholder="e.g. publicly available; licensed feed #…" />
      <Input label="Access method" value={accessMethod} onChange={setAccessMethod} placeholder="e.g. licensed search API (read-only)" />
      <Input label="Jurisdiction" value={jurisdiction} onChange={setJurisdiction} placeholder="e.g. Rhode Island, USA" />
      <Input label="Legal review note (optional)" value={note} onChange={setNote} placeholder="Reviewer / reference" />
      <div className="flex gap-2">
        <Btn type="submit" kind="primary" disabled={busy || !ready}>
          {busy ? "Authorizing…" : "Authorize"}
        </Btn>
        <Btn onClick={onCancel}>Cancel</Btn>
      </div>
    </form>
  );
}

function ReasonForm({
  label,
  busy,
  onSubmit,
  onCancel,
}: {
  label: string;
  busy: boolean;
  onSubmit: (reason: string) => void;
  onCancel: () => void;
}) {
  const [reason, setReason] = useState("");
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(reason.trim());
      }}
      className="space-y-2 rounded-md border border-surface-border bg-surface-sunken p-3"
    >
      <Input label={label} value={reason} onChange={setReason} placeholder="Recorded in the source's history" />
      <div className="flex gap-2">
        <Btn type="submit" kind="primary" disabled={busy || !reason.trim()}>
          {busy ? "Saving…" : "Confirm"}
        </Btn>
        <Btn onClick={onCancel}>Cancel</Btn>
      </div>
    </form>
  );
}

function Input({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-ink-muted">{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
      />
    </label>
  );
}

function Btn({
  children,
  onClick,
  type = "button",
  kind = "default",
  disabled,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  kind?: "primary" | "default";
  disabled?: boolean;
}) {
  const cls =
    kind === "primary"
      ? "bg-accent text-white hover:opacity-90"
      : "border border-surface-border text-ink-muted hover:bg-surface-sunken hover:text-ink";
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`rounded-md px-3 py-1.5 text-sm font-medium disabled:opacity-50 ${cls}`}
    >
      {children}
    </button>
  );
}
