"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCan } from "@/components/auth/UserContext";
import { assignMember } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { User } from "@/lib/types";

/** Assign a user to a case. Visible only to case managers / admins. */
export function AssignMemberForm({ caseId, users }: { caseId: string; users: User[] }) {
  const router = useRouter();
  const canManage = useCan("manage_case");
  const [username, setUsername] = useState(users[0]?.username ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!canManage) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const res = await assignMember(caseId, username);
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    router.refresh();
  }

  return (
    <form onSubmit={submit} className="flex items-end gap-2">
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
