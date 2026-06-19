"use client";

import { useRouter } from "next/navigation";
import { humanize } from "@/lib/format";
import type { CurrentUser, User } from "@/lib/types";

/**
 * Dev-only user switcher. Sets the `orca_user` cookie (forwarded as `X-ORCA-User`) and
 * refreshes so every server read and client mutation acts as the selected user.
 * Production replaces this with a real sign-in.
 */
export function UserSwitcher({
  users,
  current,
}: {
  users: User[];
  current: CurrentUser | null;
}) {
  const router = useRouter();

  function setUser(username: string) {
    document.cookie = `orca_user=${encodeURIComponent(username)}; path=/; max-age=31536000`;
    router.refresh();
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-ink-faint">Acting as</span>
      <select
        value={current?.username ?? ""}
        onChange={(e) => setUser(e.target.value)}
        className="rounded-md border border-surface-border bg-surface px-2 py-1 text-xs text-ink"
        title="Dev user switcher"
      >
        {users.map((u) => (
          <option key={u.id} value={u.username}>
            {u.display_name} · {humanize(u.role)}
          </option>
        ))}
      </select>
    </div>
  );
}
