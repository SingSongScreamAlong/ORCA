"use client";

import { usePathname } from "next/navigation";

const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/review": "Review Queue",
  "/cases": "Cases",
  "/observations": "Observations",
  "/intake": "Observation Intake",
  "/entities": "Entities",
  "/relationships": "Relationships",
  "/clusters": "Clusters",
  "/reports": "Reports",
  "/evidence": "Evidence",
  "/hunting": "Hunting Grounds",
  "/foundry": "Foundry Integration",
  "/audit": "System Audit",
  "/safety": "Safety & Handling",
};

export function SectionTitle() {
  const pathname = usePathname();
  const key = Object.keys(TITLES)
    .filter((k) => (k === "/" ? pathname === "/" : pathname.startsWith(k)))
    .sort((a, b) => b.length - a.length)[0];
  return <h1 className="text-base font-semibold text-ink">{TITLES[key] ?? "ORCA"}</h1>;
}
