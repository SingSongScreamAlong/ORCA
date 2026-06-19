"use client";

import { usePathname } from "next/navigation";
import { TopBar } from "./TopBar";

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
  "/safety": "Safety & Handling",
};

export function SectionTitle() {
  const pathname = usePathname();
  const key = Object.keys(TITLES)
    .filter((k) => (k === "/" ? pathname === "/" : pathname.startsWith(k)))
    .sort((a, b) => b.length - a.length)[0];
  return <TopBar title={TITLES[key] ?? "ORCA"} />;
}
