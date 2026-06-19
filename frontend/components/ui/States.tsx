/** Empty and error states. Calm, explanatory, never noisy. */

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-dashed border-surface-border px-4 py-10 text-center text-sm text-ink-faint">
      {message}
    </div>
  );
}

/**
 * Shown when a read fails. A 401/403 is a permission/identity problem (RBAC), not an
 * outage, so it is surfaced as a calm access notice rather than a backend error.
 */
export function BackendNotice({ error, status }: { error: string; status?: number }) {
  if (status === 403 || status === 401) {
    return (
      <div className="rounded-md border border-slate-200 bg-surface-sunken px-4 py-3 text-sm text-ink-muted">
        <p className="font-medium text-ink">You don&apos;t have access to this.</p>
        <p className="mt-1">
          Your role isn&apos;t permitted to view this material. Switch to a role with access using
          the user switcher, or ask a case manager for an assignment.
        </p>
        <p className="mt-2 text-xs text-ink-faint">{error}</p>
      </div>
    );
  }
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
      <p className="font-medium">The ORCA backend is not reachable.</p>
      <p className="mt-1 text-amber-700">{error}</p>
      <p className="mt-2 text-xs text-amber-700">
        Start it with <code className="mono">uvicorn app.main:app --reload</code> in{" "}
        <code className="mono">backend/</code>, then reload this page.
      </p>
    </div>
  );
}
