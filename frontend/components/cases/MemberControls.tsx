"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { deactivateMember, updateMember } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { CaseMember, CaseRole } from "@/lib/types";

const CASE_ROLES: CaseRole[] = [
  "case_manager",
  "analyst",
  "reviewer",
  "viewer",
  "partner_export_viewer",
];

/**
 * Change a member's case role or revoke their access. Rendered only for case managers /
 * admins; the backend enforces the same rule and audits every change.
 */
export function MemberControls({ member }: { member: CaseMember }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function changeRole(next: CaseRole) {
    if (next === member.case_role) return;
    setBusy(true);
    setError(null);
    const res = await updateMember(member.case_id, member.id, { case_role: next });
    setBusy(false);
    if (!res.ok) return setError(res.error);
    router.refresh();
  }

  async function revoke() {
    setBusy(true);
    setError(null);
    const res = await deactivateMember(member.case_id, member.id);
    setBusy(false);
    if (!res.ok) return setError(res.error);
    router.refresh();
  }

  const revoked = member.status === "revoked" || member.status === "inactive";

  return (
    <div className="flex items-center gap-2">
      <select
        value={member.case_role}
        disabled={busy || revoked}
        onChange={(e) => changeRole(e.target.value as CaseRole)}
        className="rounded-md border border-surface-border bg-surface px-1.5 py-1 text-xs disabled:opacity-50"
        title="Change case role"
      >
        {CASE_ROLES.map((r) => (
          <option key={r} value={r}>
            {humanize(r)}
          </option>
        ))}
      </select>
      {!revoked && (
        <button
          type="button"
          onClick={revoke}
          disabled={busy}
          className="rounded-md border border-surface-border px-2 py-1 text-xs text-ink-muted hover:text-ink disabled:opacity-50"
        >
          Revoke
        </button>
      )}
      {error && <span className="text-xs text-amber-700">{error}</span>}
    </div>
  );
}
