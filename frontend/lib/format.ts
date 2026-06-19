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

/** Human-readable byte size (e.g. 1.4 MB). */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i += 1;
  }
  return `${value.toFixed(1)} ${units[i]}`;
}
