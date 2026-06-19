import type { ReactNode } from "react";

/** Minimal, information-dense table primitives with consistent styling. */

export function Table({ head, children }: { head: ReactNode; children: ReactNode }) {
  return (
    <div className="card overflow-x-auto p-0">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-surface-border text-left">{head}</tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function Th({ children }: { children: ReactNode }) {
  return <th className="px-4 py-2.5 text-xs font-medium uppercase tracking-wide text-ink-faint">{children}</th>;
}

export function Td({ children }: { children: ReactNode }) {
  return <td className="px-4 py-3 align-top text-ink">{children}</td>;
}

export function Tr({ children }: { children: ReactNode }) {
  return <tr className="border-b border-surface-border last:border-0">{children}</tr>;
}
