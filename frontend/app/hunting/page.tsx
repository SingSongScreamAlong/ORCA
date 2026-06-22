import { Card } from "@/components/ui/Card";
import { BackendNotice, EmptyState } from "@/components/ui/States";
import { PageIntro } from "@/components/ui/PageIntro";
import { EscalationsPanel } from "@/components/hunting/EscalationsPanel";
import { FlagConcernForm } from "@/components/hunting/FlagConcernForm";
import { LogLeadForm } from "@/components/hunting/LogLeadForm";
import { ProposeSourceForm } from "@/components/hunting/ProposeSourceForm";
import { RunDiscoveryForm } from "@/components/hunting/RunDiscoveryForm";
import { SourceControls } from "@/components/hunting/SourceControls";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { getHuntingEscalations, getHuntingSources, getHuntingSummary } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { HuntingSource, HuntingSourceStatus, HuntingSummary } from "@/lib/types";

export const dynamic = "force-dynamic";

const DEFAULT_AOR = "Rhode Island";

const STATUS_STYLE: Record<HuntingSourceStatus, string> = {
  proposed: "bg-amber-50 text-amber-700 ring-amber-200",
  authorized: "bg-sky-50 text-sky-700 ring-sky-200",
  monitored: "bg-green-50 text-green-700 ring-green-200",
  suspended: "bg-slate-100 text-slate-600 ring-slate-200",
  retired: "bg-slate-100 text-slate-500 ring-slate-200",
  rejected: "bg-rose-50 text-rose-700 ring-rose-200",
};

export default async function HuntingPage() {
  const [sources, summary, escalations] = await Promise.all([
    getHuntingSources(),
    getHuntingSummary(),
    getHuntingEscalations(),
  ]);

  if (!sources.ok) {
    return (
      <div className="space-y-6">
        <Intro />
        <BackendNotice error={sources.error} status={sources.status} />
      </div>
    );
  }

  // Escalations are admin-only; the fetch 403s for everyone else, so we only show the queue
  // when it resolves (i.e. the viewer is an administrator).
  const openEscalations = escalations.ok
    ? escalations.data.filter((e) => e.status === "open" || e.status === "reported")
    : [];

  return (
    <div className="space-y-6">
      <Intro />
      <GovernanceNote />

      {escalations.ok && (
        <Card
          title="Escalations — suspected minor / CSAM"
          subtitle="Report-only, never-store. Each is a pointer; a human files the NCMEC CyberTipline report and records the reference here. ORCA stores no material."
        >
          <EscalationsPanel escalations={openEscalations} />
        </Card>
      )}

      {summary.ok && summary.data.totals.total > 0 && <AorPicture summary={summary.data} />}

      <Card
        title="Discovery"
        subtitle="Propose candidate venues in bulk (the hunt surfaces new sites so the operator need not trawl). Deduped by URL; each still requires authorization before monitoring."
      >
        <RunDiscoveryForm defaultAor={DEFAULT_AOR} />
      </Card>

      <Card
        title="Propose a source"
        subtitle="Candidates enter as 'proposed' — never monitored — until an administrator authorizes them with a lawful basis."
      >
        <ProposeSourceForm defaultAor={DEFAULT_AOR} />
      </Card>

      {sources.data.length === 0 ? (
        <EmptyState message="No sources yet. Propose a candidate above; an administrator authorizes it before anything is monitored." />
      ) : (
        <div className="space-y-4">
          {sources.data.map((s) => (
            <SourceCard key={s.id} source={s} />
          ))}
        </div>
      )}
    </div>
  );
}

const PICTURE_COLS: HuntingSourceStatus[] = [
  "proposed",
  "authorized",
  "monitored",
  "suspended",
  "retired",
  "rejected",
];

function AorPicture({ summary }: { summary: HuntingSummary }) {
  return (
    <Card
      title="AOR picture"
      subtitle="The regional posture at a glance — source counts by status, per area of responsibility."
    >
      <Table
        head={
          <>
            <Th>AOR</Th>
            {PICTURE_COLS.map((c) => (
              <Th key={c}>{humanize(c)}</Th>
            ))}
            <Th>Total</Th>
          </>
        }
      >
        {summary.aors.map((row) => (
          <Tr key={row.aor}>
            <Td>
              <span className="font-medium text-ink">{row.aor}</span>
            </Td>
            {PICTURE_COLS.map((c) => (
              <Td key={c}>
                <span className={row.by_status[c] ? "tabular-nums text-ink" : "tabular-nums text-ink-faint"}>
                  {row.by_status[c] ?? 0}
                </span>
              </Td>
            ))}
            <Td>
              <span className="tabular-nums font-medium text-ink">{row.total}</span>
            </Td>
          </Tr>
        ))}
      </Table>
    </Card>
  );
}

function SourceCard({ source }: { source: HuntingSource }) {
  return (
    <section className="card space-y-3">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-ink">{source.name}</h2>
            <StatusPill status={source.status} />
          </div>
          <p className="mono mt-0.5 text-xs text-ink-faint">{source.url}</p>
          <p className="mt-1 text-xs text-ink-muted">
            {humanize(source.category)} · AOR {source.aor} · proposed by {source.proposed_by}
            {source.authorized_by ? ` · authorized by ${source.authorized_by}` : ""}
          </p>
        </div>
        <div className="shrink-0">
          <SourceControls source={source} />
        </div>
      </div>

      {source.lawful_basis && (
        <div className="rounded-md border border-surface-border bg-surface-sunken px-3 py-2 text-xs text-ink-muted">
          <div>
            <span className="text-ink-faint">Lawful basis:</span> {source.lawful_basis}
          </div>
          <div>
            <span className="text-ink-faint">Access method:</span> {source.access_method} ·{" "}
            <span className="text-ink-faint">Jurisdiction:</span> {source.jurisdiction}
          </div>
          {source.legal_review_note && (
            <div>
              <span className="text-ink-faint">Legal review:</span> {source.legal_review_note}
            </div>
          )}
        </div>
      )}

      {source.status === "monitored" && (
        <div className="space-y-2">
          <LogLeadForm sourceId={source.id} />
          <FlagConcernForm sourceId={source.id} aor={source.aor} url={source.url} />
        </div>
      )}

      <details className="text-xs">
        <summary className="cursor-pointer text-ink-faint hover:text-ink">
          History ({source.history.length})
        </summary>
        <ol className="mt-2 space-y-1">
          {source.history.map((h, i) => (
            <li key={i} className="flex flex-wrap gap-x-2 text-ink-muted">
              <span className="mono text-ink-faint">{new Date(h.at).toLocaleString()}</span>
              <span>
                {h.from_status ? `${humanize(h.from_status)} → ` : ""}
                <span className="font-medium text-ink">{humanize(h.to_status)}</span>
              </span>
              <span className="text-ink-faint">by {h.by}</span>
              {h.note && <span>— {h.note}</span>}
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}

function StatusPill({ status }: { status: HuntingSourceStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${STATUS_STYLE[status]}`}
    >
      {humanize(status)}
    </span>
  );
}

function GovernanceNote() {
  return (
    <div className="rounded-md border border-sky-200 bg-sky-50 px-4 py-2.5 text-sm text-sky-800">
      This registry <span className="font-medium">governs which sources may be monitored</span> — it
      does not monitor or collect anything. Auto-discovery (later) can only ever create proposals;
      an administrator authorizes a source, with a recorded lawful basis, before it is ever watched.
    </div>
  );
}

function Intro() {
  return (
    <PageIntro>
      Hunting Grounds is ORCA&apos;s reconnaissance layer — it takes the manual trawling off the
      operator. This is the source registry: the authorization-first gate from the{" "}
      <a className="text-accent hover:underline" href="https://github.com/SingSongScreamAlong/ORCA/blob/main/docs/hunting_grounds_charter.md">
        charter
      </a>
      . Operators propose candidate venues; administrators authorize them with a lawful basis
      before anything is monitored.
    </PageIntro>
  );
}
