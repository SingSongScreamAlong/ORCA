/**
 * A quiet top bar. Holds the current section title and leaves room for future
 * controls (search, the acting analyst) without competing with the content.
 */
export function TopBar({ title }: { title: string }) {
  return (
    <header className="flex h-14 items-center justify-between border-b border-surface-border bg-surface px-8">
      <h1 className="text-base font-semibold text-ink">{title}</h1>
      <div className="text-xs text-ink-faint">Development Analyst · reviewer</div>
    </header>
  );
}
