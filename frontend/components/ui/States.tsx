/** Empty and error states. Calm, explanatory, never noisy. */

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-dashed border-surface-border px-4 py-10 text-center text-sm text-ink-faint">
      {message}
    </div>
  );
}

/**
 * Shown when the backend cannot be reached. The skeleton runs the API separately, so
 * this is informative rather than an error to panic over.
 */
export function BackendNotice({ error }: { error: string }) {
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
