"use client";

import { createContext, useContext } from "react";
import type { CurrentUser } from "@/lib/types";

const UserCtx = createContext<CurrentUser | null>(null);

export function UserProvider({
  value,
  children,
}: {
  value: CurrentUser | null;
  children: React.ReactNode;
}) {
  return <UserCtx.Provider value={value}>{children}</UserCtx.Provider>;
}

export function useUser(): CurrentUser | null {
  return useContext(UserCtx);
}

/** Whether the current user's role grants a capability. */
export function useCan(capability: string): boolean {
  const user = useContext(UserCtx);
  return !!user && user.capabilities.includes(capability);
}
