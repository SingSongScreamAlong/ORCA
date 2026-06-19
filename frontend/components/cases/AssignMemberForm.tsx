"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { assignMember } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { CaseRole, User } from "@/lib/types";

const CASE_ROLES: CaseRole[] = [
  "case_manager",
  "analyst",
  "reviewer",
  "viewer",
  "partner_export_viewer",
];

/**
 * Assign a user to a case with an explicit case role. Rendered only when the viewer may
 * manage this case's roster (an administrator or the case's manager); the backend
 * enforces the same rule regardless.
 */
export function AssignMemberForm({
  caseId,
  users,
  canManage,
}: {
  caseId: string;
  users: User[];
  canManage: boolean;
}) {
  const router = useRouter();
  const [username, setUsername] = useState(users[0]?.username ?? "");
  const [caseRole, setCaseRole] = useState<CaseRole | "">("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!canManage) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const res = await assignMember(caseId, username, caseRole || undefined);
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    router.refresh();
  }

  return (
    <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
      <div>
        <label className="mb-1 block text-xs font-medium text-ink-muted">Assign user</label>
        <select
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
        >
          {users.map((u) => (
            <option key={u.id} value={u.username}>
              {u.display_name} · {humanize(u.role)}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-ink-muted">Case role</label>
        <select
          value={caseRole}
          onChange={(e) => setCaseRole(e.target.value as CaseRole | "")}
          className="rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm"
        >
          <option value="">From global role</option>
          {CASE_ROLES.map((r) => (
            <option key={r} value={r}>
              {humanize(r)}
            </option>
          ))}
        </select>
      </div>
      <button
        type="submit"
        disabled={busy}
        className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
      >
        {busy ? "Assigning…" : "Assign"}
      </button>
      {error && <span className="self-center text-xs text-amber-700">{error}</span>}
    </form>
  );
}
