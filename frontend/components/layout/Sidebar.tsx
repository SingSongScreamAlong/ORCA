"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * Primary navigation. One entry per ontology object, plus the dashboard and the
 * review queue. The review queue is visually separated because it is where decisions
 * are made.
 */
const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/review", label: "Review Queue", emphasis: true },
  { href: "/cases", label: "Cases" },
  { href: "/observations", label: "Observations" },
  { href: "/entities", label: "Entities" },
  { href: "/relationships", label: "Relationships" },
  { href: "/clusters", label: "Clusters" },
  { href: "/reports", label: "Reports" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className="flex h-full w-56 shrink-0 flex-col border-r border-surface-border bg-surface px-3 py-5">
      <div className="px-2 pb-6">
        <div className="text-lg font-semibold tracking-tight text-ink">ORCA</div>
        <div className="text-xs text-ink-faint">
          Observation · Reconnaissance
          <br />
          Collection · Analysis
        </div>
      </div>

      <ul className="flex flex-col gap-1">
        {NAV.map((item) => {
          const active =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                className={[
                  "block rounded-md px-3 py-2 text-sm transition-colors",
                  active
                    ? "bg-accent-soft font-medium text-accent"
                    : "text-ink-muted hover:bg-surface-sunken hover:text-ink",
                  item.emphasis && !active ? "font-medium text-ink" : "",
                ].join(" ")}
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>

      <div className="mt-6 space-y-1 border-t border-surface-border pt-3">
        <Link
          href="/hunting"
          className={[
            "block rounded-md px-3 py-2 text-sm transition-colors",
            pathname.startsWith("/hunting")
              ? "bg-accent-soft font-medium text-accent"
              : "text-ink-muted hover:bg-surface-sunken hover:text-ink",
          ].join(" ")}
        >
          Hunting Grounds
        </Link>
        <Link
          href="/foundry"
          className={[
            "block rounded-md px-3 py-2 text-sm transition-colors",
            pathname.startsWith("/foundry")
              ? "bg-accent-soft font-medium text-accent"
              : "text-ink-muted hover:bg-surface-sunken hover:text-ink",
          ].join(" ")}
        >
          Foundry <span className="text-[0.65rem] text-ink-faint">(admin)</span>
        </Link>
        <Link
          href="/safety"
          className={[
            "block rounded-md px-3 py-2 text-sm transition-colors",
            pathname.startsWith("/safety")
              ? "bg-accent-soft font-medium text-accent"
              : "text-ink-muted hover:bg-surface-sunken hover:text-ink",
          ].join(" ")}
        >
          Safety &amp; Handling
        </Link>
      </div>

      <div className="mt-auto px-2 pt-6 text-[0.7rem] leading-relaxed text-ink-faint">
        AI proposes. Analysts decide.
        <br />
        Every conclusion is human-reviewed.
      </div>
    </nav>
  );
}
