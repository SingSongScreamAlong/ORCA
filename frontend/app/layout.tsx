import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/Sidebar";
import { SectionTitle } from "@/components/layout/SectionTitle";
import { UserProvider } from "@/components/auth/UserContext";
import { UserSwitcher } from "@/components/auth/UserSwitcher";
import { getMe, getUsers } from "@/lib/api";
import "./globals.css";

export const metadata: Metadata = {
  title: "ORCA",
  description:
    "ORCA preserves observations, discovers relationships, and maintains institutional intelligence memory. The system proposes; analysts decide.",
};

export const dynamic = "force-dynamic";

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const [me, users] = await Promise.all([getMe(), getUsers()]);
  const current = me.ok ? me.data : null;
  const userList = users.ok ? users.data : [];

  return (
    <html lang="en">
      <body>
        <UserProvider value={current}>
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <div className="flex min-w-0 flex-1 flex-col">
              <header className="flex h-14 items-center justify-between border-b border-surface-border bg-surface px-8">
                <SectionTitle />
                <UserSwitcher users={userList} current={current} />
              </header>
              <main className="flex-1 overflow-y-auto px-8 py-7">{children}</main>
            </div>
          </div>
        </UserProvider>
      </body>
    </html>
  );
}
