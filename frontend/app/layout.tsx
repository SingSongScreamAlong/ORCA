import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/Sidebar";
import { SectionTitle } from "@/components/layout/SectionTitle";
import "./globals.css";

export const metadata: Metadata = {
  title: "ORCA",
  description:
    "ORCA preserves observations, discovers relationships, and maintains institutional intelligence memory. The system proposes; analysts decide.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <div className="flex min-w-0 flex-1 flex-col">
            <SectionTitle />
            <main className="flex-1 overflow-y-auto px-8 py-7">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
