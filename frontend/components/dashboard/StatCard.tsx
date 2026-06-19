export function StatCard({
  label,
  value,
  hint,
  emphasis,
}: {
  label: string;
  value: number | string;
  hint?: string;
  emphasis?: boolean;
}) {
  return (
    <div className="card">
      <div className="label">{label}</div>
      <div
        className={`mt-2 text-3xl font-semibold tabular-nums ${
          emphasis ? "text-accent" : "text-ink"
        }`}
      >
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-ink-faint">{hint}</div>}
    </div>
  );
}
