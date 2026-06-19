/** A short, plain description under a page title. Sets context without filler. */
export function PageIntro({ children }: { children: React.ReactNode }) {
  return <p className="mb-6 max-w-3xl text-sm text-ink-muted">{children}</p>;
}
