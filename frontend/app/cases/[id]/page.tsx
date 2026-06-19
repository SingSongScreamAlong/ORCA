import Link from "next/link";
import { notFound } from "next/navigation";
import { AssignMemberForm } from "@/components/cases/AssignMemberForm";
import { MemberControls } from "@/components/cases/MemberControls";
import { GenerateReportButton } from "@/components/cases/GenerateReportButton";
import { CapLink } from "@/components/auth/CapLink";
import { CaseGraph } from "@/components/graph/CaseGraph";
import { EvidenceLocker } from "@/components/evidence/EvidenceLocker";
import { EvidenceUploadForm } from "@/components/evidence/EvidenceUploadForm";
import { ConfidenceBadge, OriginBadge, StatusBadge, Tag } from "@/components/ui/Badges";
import { Card } from "@/components/ui/Card";
import { EntityChip } from "@/components/ui/EntityChip";
import { StatCard } from "@/components/dashboard/StatCard";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { BackendNotice, EmptyState } from "@/components/ui/States";
import {
  getCase,
  getCaseAudit,
  getCaseEvidence,
  getCaseGraph,
  getCaseMembers,
  getCaseObservations,
  getCaseRelationships,
  getCaseReports,
  getCaseTimeline,
  getEntities,
  getMe,
  getSources,
  getUsers,
} from "@/lib/api";
import { formatTimestamp, humanize, shortId } from "@/lib/format";
import type { Case, CaseCounts, CaseMember, Entity } from "@/lib/types";

export const dynamic = "force-dynamic";

const TABS = [
  ["overview", "Overview"],
  ["observations", "Observations"],
  ["evidence", "Evidence Locker"],
  ["relationships", "Relationships"],
  ["graph", "Graph"],
  ["timeline", "Timeline"],
  ["members", "Members"],
  ["audit", "Audit log"],
  ["report", "Draft report"],
] as const;

export default async function CaseDetailPage({
  params,
  searchParams,
}: {
  params: { id: string };
  searchParams: { tab?: string };
}) {
  const detail = await getCase(params.id);
  if (!detail.ok) {
    if (detail.error.includes("404")) notFound();
    return <BackendNotice error={detail.error} status={detail.status} />;
  }
  const { case: c, counts } = detail.data;
  const tab = searchParams.tab ?? "overview";

  // The viewer's standing on THIS case (need-to-know): their case role and whether they
  // may manage the roster. Administrators act as case managers everywhere.
  const [meRes, membersRes] = await Promise.all([getMe(), getCaseMembers(params.id)]);
  const me = meRes.ok ? meRes.data : null;
  const members = membersRes.ok ? membersRes.data : [];
  const myMembership = members.find((m) => me && m.user_id === me.id && m.status === "active");
  const myCaseRole = me?.role === "admin" ? "admin" : myMembership?.case_role ?? null;
  const canManage = me?.role === "admin" || myMembership?.case_role === "case_manager";

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-ink">{c.title}</h2>
            <Tag>{humanize(c.status)}</Tag>
            {myCaseRole && (
              <span className="rounded-full bg-surface-sunken px-2 py-0.5 text-xs text-ink-muted">
                Your access: {humanize(myCaseRole)}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-ink-faint">
            Owner {c.owner} · created {formatTimestamp(c.created_at)}
          </p>
        </div>
        <CapLink
          cap="create_observation"
          href={`/intake?case=${c.id}`}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90"
        >
          + Add observation
        </CapLink>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-surface-border">
        {TABS.map(([key, label]) => (
          <Link
            key={key}
            href={`/cases/${c.id}?tab=${key}`}
            className={[
              "border-b-2 px-3 py-2 text-sm",
              tab === key
                ? "border-accent font-medium text-accent"
                : "border-transparent text-ink-muted hover:text-ink",
            ].join(" ")}
          >
            {label}
          </Link>
        ))}
      </div>

      {tab === "overview" && <Overview c={c} counts={counts} />}
      {tab === "observations" && <Observations caseId={c.id} />}
      {tab === "evidence" && <EvidenceTab caseId={c.id} />}
      {tab === "relationships" && <Relationships caseId={c.id} />}
      {tab === "graph" && <Graph caseId={c.id} />}
      {tab === "timeline" && <Timeline caseId={c.id} />}
      {tab === "members" && (
        <Members
          caseId={c.id}
          members={members}
          canManage={canManage}
          currentUserId={me?.id ?? null}
        />
      )}
      {tab === "audit" && <Audit caseId={c.id} />}
      {tab === "report" && <ReportTab caseId={c.id} />}
    </div>
  );
}

function Overview({ c, counts }: { c: Case; counts: CaseCounts }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Observations" value={counts.observations_total} />
        <StatCard label="Approved" value={counts.observations_approved} />
        <StatCard label="Pending review" value={counts.observations_pending} emphasis />
        <StatCard label="Relationships" value={counts.relationships} />
      </div>
      <Card title="Summary">
        <p className="text-sm text-ink-muted">{c.summary || "No summary."}</p>
      </Card>
      <Card title="Legal & handling">
        <p className="text-sm text-ink-muted">{c.legal_notes || "No legal notes recorded."}</p>
      </Card>
    </div>
  );
}

async function _entityMap(): Promise<Map<string, Entity>> {
  const entities = await getEntities();
  return new Map<string, Entity>(entities.ok ? entities.data.map((e) => [e.id, e]) : []);
}

async function Observations({ caseId }: { caseId: string }) {
  const [obs, entityMap] = await Promise.all([getCaseObservations(caseId), _entityMap()]);
  if (!obs.ok) return <BackendNotice error={obs.error} status={obs.status} />;
  if (obs.data.length === 0) return <EmptyState message="No observations in this case yet." />;
  return (
    <Table
      head={
        <>
          <Th>Observation</Th>
          <Th>Status</Th>
          <Th>References</Th>
          <Th>Handling</Th>
          <Th>Confidence</Th>
        </>
      }
    >
      {obs.data.map((o) => (
        <Tr key={o.id}>
          <Td>
            <div className="max-w-md text-ink">{o.notes ?? "(no notes)"}</div>
            <div className="mono mt-0.5 text-xs text-ink-faint">{shortId(o.id)}</div>
          </Td>
          <Td>
            <StatusBadge status={o.status} />
          </Td>
          <Td>
            <div className="flex flex-wrap gap-1">
              {o.entity_ids.map((id) => (
                <EntityChip key={id} entity={entityMap.get(id)} fallbackId={id} />
              ))}
            </div>
          </Td>
          <Td>
            <div className="flex flex-wrap gap-1 text-xs text-ink-faint">
              {o.handling.requires_legal_review && <Tag>legal review</Tag>}
              {o.handling.sensitive && <Tag>sensitive</Tag>}
              {!o.handling.requires_legal_review && !o.handling.sensitive && "—"}
            </div>
          </Td>
          <Td>
            <ConfidenceBadge value={o.confidence} />
          </Td>
        </Tr>
      ))}
    </Table>
  );
}

async function Relationships({ caseId }: { caseId: string }) {
  const [rels, entityMap] = await Promise.all([getCaseRelationships(caseId), _entityMap()]);
  if (!rels.ok) return <BackendNotice error={rels.error} status={rels.status} />;
  if (rels.data.length === 0) {
    return <EmptyState message="No relationships yet. Approve observations, then link them." />;
  }
  return (
    <Table
      head={
        <>
          <Th>Type</Th>
          <Th>Between</Th>
          <Th>Origin</Th>
          <Th>Support</Th>
          <Th>Status</Th>
          <Th>Confidence</Th>
        </>
      }
    >
      {rels.data.map((r) => (
        <Tr key={r.id}>
          <Td>
            <Tag>{humanize(r.relationship_type)}</Tag>
          </Td>
          <Td>
            <div className="flex flex-wrap items-center gap-1.5">
              <EntityChip entity={entityMap.get(r.source_entity_id)} fallbackId={r.source_entity_id} />
              <span className="text-ink-faint">—</span>
              <EntityChip entity={entityMap.get(r.target_entity_id)} fallbackId={r.target_entity_id} />
            </div>
          </Td>
          <Td>
            <OriginBadge origin={r.origin} />
          </Td>
          <Td>
            <span className="text-ink-muted">{r.observation_ids.length}</span>{" "}
            <span className="text-ink-faint">obs.</span>
          </Td>
          <Td>
            <StatusBadge status={r.status} />
          </Td>
          <Td>
            <ConfidenceBadge value={r.confidence} />
          </Td>
        </Tr>
      ))}
    </Table>
  );
}

async function Graph({ caseId }: { caseId: string }) {
  const graph = await getCaseGraph(caseId);
  if (!graph.ok) return <BackendNotice error={graph.error} status={graph.status} />;
  if (graph.data.edges.length === 0) {
    return (
      <EmptyState message="No approved relationships to graph yet. Approve observations and link entities." />
    );
  }
  return (
    <Card
      title="Relationship graph"
      subtitle="Approved relationships only. Nodes are entities; edges are the links between them."
    >
      <CaseGraph view={graph.data} />
    </Card>
  );
}

async function EvidenceTab({ caseId }: { caseId: string }) {
  const [evidence, observations, sources] = await Promise.all([
    getCaseEvidence(caseId),
    getCaseObservations(caseId),
    getSources(),
  ]);
  if (!evidence.ok) return <BackendNotice error={evidence.error} status={evidence.status} />;

  const sourceNames: Record<string, string> = {};
  if (sources.ok) for (const s of sources.data) sourceNames[s.id] = s.name;
  const observationLabels: Record<string, string> = {};
  if (observations.ok) {
    for (const o of observations.data) observationLabels[o.id] = (o.notes ?? o.id).slice(0, 50);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-ink-faint">
          Metadata, lawful files, and partner-approved workflows only. Verify hashes; decide each item.
        </p>
        <CapLink
          cap="create_evidence"
          href={`/evidence/new?case=${caseId}`}
          className="rounded-md border border-surface-border px-3 py-1.5 text-sm font-medium text-ink hover:bg-surface-sunken"
        >
          + Record metadata only
        </CapLink>
      </div>
      <EvidenceUploadForm caseId={caseId} sources={sources.ok ? sources.data : []} />
      <EvidenceLocker items={evidence.data} sources={sourceNames} observations={observationLabels} />
    </div>
  );
}

async function Members({
  caseId,
  members,
  canManage,
  currentUserId,
}: {
  caseId: string;
  members: CaseMember[];
  canManage: boolean;
  currentUserId: string | null;
}) {
  const users = await getUsers();
  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-faint">
        Access is need-to-know: only active members may open this case, and each member&apos;s
        case role decides what they can do here. Membership changes are audited.
      </p>
      <AssignMemberForm caseId={caseId} users={users.ok ? users.data : []} canManage={canManage} />
      {members.length === 0 ? (
        <EmptyState message="No members assigned to this case yet." />
      ) : (
        <Table
          head={
            <>
              <Th>User</Th>
              <Th>Global role</Th>
              <Th>Case role</Th>
              <Th>Status</Th>
              <Th>Assigned by</Th>
              <Th>When</Th>
              {canManage && <Th>Manage</Th>}
            </>
          }
        >
          {members.map((m) => (
            <Tr key={m.id}>
              <Td>
                <div className="text-ink">{m.display_name}</div>
                <div className="mono mt-0.5 text-xs text-ink-faint">{m.username}</div>
              </Td>
              <Td>
                <Tag>{humanize(m.global_role)}</Tag>
              </Td>
              <Td>
                <Tag>{humanize(m.case_role)}</Tag>
              </Td>
              <Td>
                <MemberStatus status={m.status} />
              </Td>
              <Td>{m.assigned_by}</Td>
              <Td>{formatTimestamp(m.assigned_at)}</Td>
              {canManage && (
                <Td>
                  {m.user_id === currentUserId ? (
                    <span className="text-xs text-ink-faint">—</span>
                  ) : (
                    <MemberControls member={m} />
                  )}
                </Td>
              )}
            </Tr>
          ))}
        </Table>
      )}
    </div>
  );
}

function MemberStatus({ status }: { status: CaseMember["status"] }) {
  const tone =
    status === "active"
      ? "bg-emerald-50 text-emerald-700"
      : "bg-slate-100 text-ink-muted";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs ${tone}`}>{humanize(status)}</span>
  );
}

async function Timeline({ caseId }: { caseId: string }) {
  const events = await getCaseTimeline(caseId);
  if (!events.ok) return <BackendNotice error={events.error} status={events.status} />;
  if (events.data.length === 0) {
    return <EmptyState message="The timeline shows approved observations and relationship changes." />;
  }
  return (
    <ol className="relative space-y-4 border-l border-surface-border pl-6">
      {events.data.map((e, i) => (
        <li key={i} className="relative">
          <span className="absolute -left-[1.6rem] top-1 h-2.5 w-2.5 rounded-full bg-accent" />
          <div className="text-xs text-ink-faint">{formatTimestamp(e.timestamp)}</div>
          <div className="text-sm text-ink">
            <span className="font-medium">{humanize(e.kind)}</span> — {e.summary}
          </div>
        </li>
      ))}
    </ol>
  );
}

async function Audit({ caseId }: { caseId: string }) {
  const audit = await getCaseAudit(caseId);
  if (!audit.ok) return <BackendNotice error={audit.error} status={audit.status} />;
  if (audit.data.length === 0) return <EmptyState message="No audited actions yet." />;
  return (
    <Table
      head={
        <>
          <Th>When</Th>
          <Th>Actor</Th>
          <Th>Action</Th>
          <Th>Target</Th>
        </>
      }
    >
      {audit.data.map((a) => (
        <Tr key={a.id}>
          <Td>{formatTimestamp(a.created_at)}</Td>
          <Td>{a.actor_id}</Td>
          <Td>
            <span className="mono text-xs">{a.action}</span>
          </Td>
          <Td>
            <span className="text-ink-faint">{a.target_type}</span>{" "}
            <span className="mono text-xs">{shortId(a.target_id)}</span>
          </Td>
        </Tr>
      ))}
    </Table>
  );
}

async function ReportTab({ caseId }: { caseId: string }) {
  const reports = await getCaseReports(caseId);
  const latest = reports.ok && reports.data.length > 0 ? reports.data[0] : null;
  return (
    <div className="space-y-4">
      <Card
        title="Draft report"
        subtitle="Generated from approved evidence only — proposed and rejected observations are excluded."
        actions={
          <GenerateReportButton
            caseId={caseId}
            latestReportId={latest?.id}
            latestStatus={latest?.status}
          />
        }
      >
        {!reports.ok ? (
          <BackendNotice error={reports.error} status={reports.status} />
        ) : !latest ? (
          <EmptyState message="No report yet. Generate a draft from the approved evidence." />
        ) : (
          <div>
            <div className="mb-3 text-xs text-ink-faint">
              {latest.title} · {humanize(latest.status)} · {formatTimestamp(latest.created_at)}
            </div>
            <pre className="overflow-x-auto whitespace-pre-wrap rounded-md bg-surface-sunken p-4 text-sm text-ink">
              {latest.body}
            </pre>
          </div>
        )}
      </Card>
    </div>
  );
}
