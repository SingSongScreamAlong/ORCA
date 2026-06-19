import { confidenceBand, confidencePercent, humanize } from "@/lib/format";
import type { Origin, ReviewStatus } from "@/lib/types";

/** Confidence shown as a band, percentage, and a calm color — never alarmist. */
export function ConfidenceBadge({ value }: { value: number }) {
  const band = confidenceBand(value);
  const color: Record<string, string> = {
    unverified: "text-band-unverified",
    low: "text-band-low",
    medium: "text-band-medium",
    high: "text-band-high",
    confirmed: "text-band-confirmed",
  };
  return (
    <span className="inline-flex items-baseline gap-1.5">
      <span className={`text-xs font-semibold ${color[band]}`}>{humanize(band)}</span>
      <span className="text-xs tabular-nums text-ink-faint">{confidencePercent(value)}</span>
    </span>
  );
}

const STATUS_STYLE: Record<ReviewStatus, string> = {
  proposed: "bg-amber-50 text-amber-700 ring-amber-200",
  confirmed: "bg-green-50 text-green-700 ring-green-200",
  rejected: "bg-slate-100 text-slate-500 ring-slate-200",
  needs_review: "bg-sky-50 text-sky-700 ring-sky-200",
};

export function StatusBadge({ status }: { status: ReviewStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${STATUS_STYLE[status]}`}
    >
      {humanize(status)}
    </span>
  );
}

/** Marks whether something was system-proposed or analyst-created. */
export function OriginBadge({ origin }: { origin: Origin }) {
  const label = origin === "system_proposed" ? "Proposed by system" : humanize(origin);
  return <span className="text-xs text-ink-faint">{label}</span>;
}

/** A neutral chip for enum-ish values (types, kinds). */
export function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded bg-surface-sunken px-2 py-0.5 text-xs font-medium text-ink-muted ring-1 ring-inset ring-surface-border">
      {children}
    </span>
  );
}
