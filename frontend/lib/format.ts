// Presentation helpers: confidence bands, labels, and timestamps.

import type { ConfidenceBand } from "./types";

/** Map a numeric confidence in [0, 1] to its qualitative band (matches the backend). */
export function confidenceBand(value: number): ConfidenceBand {
  if (value < 0.2) return "unverified";
  if (value < 0.4) return "low";
  if (value < 0.7) return "medium";
  if (value < 0.9) return "high";
  return "confirmed";
}

export function confidencePercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

/** Turn a snake_case enum value into a readable label. */
export function humanize(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function shortId(id: string): string {
  return id.slice(0, 8);
}
