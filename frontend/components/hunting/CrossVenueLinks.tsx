"use client";

import { Fragment, useState } from "react";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { getHuntingIdentifierDossier } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { IdentifierDossier, IntelIdentifier } from "@/lib/types";

/**
 * Cross-venue identifiers with a drill-down pivot. Each row is a strong case lead — an identifier
 * located from two or more monitored venues. Clicking one fetches its dossier: every venue and AOR
 * it appears in, the text leads, and the identifiers it co-occurs with — the per-identifier view an
 * analyst folds into an LE referral. Read-only; pointers and metadata only (no media).
 */
export function CrossVenueLinks({ identifiers }: { identifiers: IntelIdentifier[] }) {
  const [openKey, setOpenKey] = useState<string | null>(null);
  const [dossier, setDossier] = useState<IdentifierDossier | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggle(i: IntelIdentifier) {
    const key = `${i.entity_type}:${i.value}`;
    if (openKey === key) {
      setOpenKey(null);
      setDossier(null);
      return;
    }
    setOpenKey(key);
    setDossier(null);
    setError(null);
    setLoading(true);
    const res = await getHuntingIdentifierDossier(i.entity_type, i.value);
    setLoading(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setDossier(res.data);
  }

  return (
    <Table
      head={
        <>
          <Th>Identifier</Th>
          <Th>Type</Th>
          <Th>Venues</Th>
          <Th>Leads</Th>
          <Th>Seen across</Th>
        </>
      }
    >
      {identifiers.map((i, idx) => {
        const key = `${i.entity_type}:${i.value}`;
        const open = openKey === key;
        return (
          <Fragment key={idx}>
            <Tr>
              <Td>
                <button
                  type="button"
                  onClick={() => toggle(i)}
                  aria-expanded={open}
                  aria-label={`Pivot on ${i.value} — locate it across all venues`}
                  className="mono text-left text-xs text-accent hover:underline"
                >
                  {open ? "▾ " : "▸ "}
                  {i.value}
                </button>
              </Td>
              <Td>
                <span className="text-xs text-ink-muted">{humanize(i.entity_type)}</span>
              </Td>
              <Td>
                <span className="inline-flex items-center rounded bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent">
                  {i.source_count} venues
                </span>
              </Td>
              <Td>
                <span className="tabular-nums text-xs text-ink-muted">{i.lead_count}</span>
              </Td>
              <Td>
                <span className="text-xs text-ink-faint">{i.sources.join(" · ")}</span>
              </Td>
            </Tr>
            {open && (
              <tr className="border-b border-surface-border last:border-0">
                <td colSpan={5} className="bg-surface-sunken px-4 py-3">
                  {loading ? (
                    <p className="text-xs text-ink-faint">Locating across all monitored venues…</p>
                  ) : error ? (
                    <p className="text-xs text-amber-700">{error}</p>
                  ) : dossier ? (
                    <DossierDetail dossier={dossier} />
                  ) : null}
                </td>
              </tr>
            )}
          </Fragment>
        );
      })}
    </Table>
  );
}

function DossierDetail({ dossier }: { dossier: IdentifierDossier }) {
  return (
    <div className="space-y-3">
      <p className="text-xs text-ink-muted">
        Located in <span className="font-medium text-ink">{dossier.venue_count}</span> venue(s) ·{" "}
        <span className="font-medium text-ink">{dossier.lead_count}</span> lead(s) · across{" "}
        <span className="text-ink">{dossier.aors.join(", ") || "—"}</span>
      </p>

      <div>
        <div className="mb-1 text-xs font-medium text-ink-muted">Where it appears</div>
        <ul className="space-y-1.5">
          {dossier.appearances.map((a) => (
            <li key={a.observation_id} className="text-xs text-ink-muted">
              <div className="flex flex-wrap items-center gap-x-2">
                <a
                  href={a.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-accent hover:underline"
                >
                  {a.source_name}
                </a>
                <span className="text-ink-faint">{a.aor}</span>
                <span className="mono text-ink-faint">
                  {new Date(a.observed_at).toLocaleDateString()}
                </span>
                <span className="text-ink-faint">· {humanize(a.status)}</span>
              </div>
              {a.summary && <div className="mt-0.5 text-ink">{a.summary}</div>}
            </li>
          ))}
        </ul>
      </div>

      {dossier.co_occurring.length > 0 && (
        <div>
          <div className="mb-1 text-xs font-medium text-ink-muted">
            Located alongside <span className="text-ink-faint">(link candidates)</span>
          </div>
          <ul className="flex flex-wrap gap-1.5">
            {dossier.co_occurring.map((c, idx) => (
              <li
                key={idx}
                className="inline-flex items-center gap-1.5 rounded-md border border-surface-border bg-surface px-2 py-1 text-xs"
                title={`Shares ${c.shared_leads} lead(s)`}
              >
                <span className="mono text-ink">{c.value}</span>
                <span className="text-ink-faint">{humanize(c.entity_type)}</span>
                <span className="tabular-nums text-ink-faint">×{c.shared_leads}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
