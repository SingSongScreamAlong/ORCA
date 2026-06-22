import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { Tag } from "@/components/ui/Badges";
import { BackendNotice, EmptyState } from "@/components/ui/States";
import { PageIntro } from "@/components/ui/PageIntro";
import { getFoundryDiscover, getFoundryObjects } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { FoundryObjectType } from "@/lib/types";

export const dynamic = "force-dynamic";

/**
 * Admin-only, read-only preview of the connected Foundry tenant. Renders exactly what the
 * backend's `/integrations/foundry/*` endpoints return — the frontend holds no Foundry
 * credentials and issues no writes. Non-admins get a calm access notice (the backend 403s).
 */
export default async function FoundryPage({
  searchParams,
}: {
  searchParams: { type?: string };
}) {
  const discover = await getFoundryDiscover();

  if (!discover.ok) {
    return (
      <div className="space-y-6">
        <Intro />
        <BackendNotice error={discover.error} status={discover.status} />
      </div>
    );
  }

  const { mode, ontologies, object_types: objectTypes = [] } = discover.data;
  const selectedType = searchParams.type;

  return (
    <div className="space-y-6">
      <Intro />
      <ModeBanner mode={mode} />

      <Card title="Ontologies" subtitle="Ontologies this credential can read (metadata only).">
        {ontologies.length === 0 ? (
          <EmptyState message="No ontologies visible to this credential." />
        ) : (
          <Table
            head={
              <>
                <Th>Display name</Th>
                <Th>API name</Th>
                <Th>RID</Th>
              </>
            }
          >
            {ontologies.map((o) => (
              <Tr key={o.apiName}>
                <Td>{o.displayName ?? "—"}</Td>
                <Td>
                  <span className="mono text-xs text-ink-muted">{o.apiName}</span>
                </Td>
                <Td>
                  <span className="mono text-xs text-ink-faint">{o.rid ?? "—"}</span>
                </Td>
              </Tr>
            ))}
          </Table>
        )}
      </Card>

      <Card
        title="Object types"
        subtitle="Object types in the configured ontology. Select one to preview a few records (read-only)."
      >
        {objectTypes.length === 0 ? (
          <EmptyState message="No object types — set ORCA_FOUNDRY_ONTOLOGY_API_NAME, or this ontology has none published." />
        ) : (
          <Table
            head={
              <>
                <Th>Display name</Th>
                <Th>API name</Th>
                <Th>Primary key</Th>
                <Th>Preview</Th>
              </>
            }
          >
            {objectTypes.map((t: FoundryObjectType) => (
              <Tr key={t.apiName}>
                <Td>{t.displayName ?? "—"}</Td>
                <Td>
                  <span className="mono text-xs text-ink-muted">{t.apiName}</span>
                </Td>
                <Td>
                  <span className="mono text-xs text-ink-faint">{t.primaryKey ?? "—"}</span>
                </Td>
                <Td>
                  <Link
                    href={`/foundry?type=${encodeURIComponent(t.apiName)}`}
                    scroll={false}
                    className={[
                      "text-xs font-medium",
                      selectedType === t.apiName
                        ? "text-accent"
                        : "text-accent hover:underline",
                    ].join(" ")}
                  >
                    {selectedType === t.apiName ? "Selected" : "Preview →"}
                  </Link>
                </Td>
              </Tr>
            ))}
          </Table>
        )}
      </Card>

      {selectedType && <SamplePreview objectType={selectedType} />}
    </div>
  );
}

async function SamplePreview({ objectType }: { objectType: string }) {
  const res = await getFoundryObjects(objectType, 5);
  return (
    <Card
      title={`Sample: ${objectType}`}
      subtitle="Up to 5 records, read-only. A read of the live tenant — no records are modified."
    >
      {!res.ok ? (
        <BackendNotice error={res.error} status={res.status} />
      ) : res.data.objects.length === 0 ? (
        <EmptyState message={`No records returned for ${objectType}.`} />
      ) : (
        <div className="space-y-4">
          {res.data.objects.map((obj, i) => (
            <ObjectCard key={i} obj={obj} />
          ))}
        </div>
      )}
    </Card>
  );
}

function ObjectCard({ obj }: { obj: Record<string, unknown> }) {
  const title =
    (obj.__title as string) ?? (obj.title as string) ?? (obj.__primaryKey as string) ?? "Object";
  // Show real properties; collapse Foundry's internal __-prefixed keys to the foot.
  const entries = Object.entries(obj).filter(([k]) => !k.startsWith("__"));
  return (
    <div className="rounded-md border border-surface-border bg-surface-sunken px-4 py-3">
      <div className="mb-2 text-sm font-medium text-ink">{title}</div>
      <dl className="grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-2">
        {entries.map(([k, v]) => (
          <div key={k} className="flex items-baseline justify-between gap-3 border-b border-surface-border/60 py-1">
            <dt className="text-xs text-ink-faint">{humanize(k)}</dt>
            <dd className="mono max-w-[60%] truncate text-right text-xs text-ink-muted" title={fmt(v)}>
              {fmt(v)}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function fmt(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") return String(v);
  return JSON.stringify(v);
}

function ModeBanner({ mode }: { mode: "mock" | "real" }) {
  if (mode === "real") {
    return (
      <div className="rounded-md border border-green-200 bg-green-50 px-4 py-2.5 text-sm text-green-800">
        <span className="font-medium">Live tenant</span> — reading the connected Foundry tenant
        (read-only).
      </div>
    );
  }
  return (
    <div className="rounded-md border border-sky-200 bg-sky-50 px-4 py-2.5 text-sm text-sky-800">
      <span className="font-medium">Mock mode</span> — Foundry is disabled, so this shows
      deterministic synthetic data. Enable it with{" "}
      <code className="mono">ORCA_FOUNDRY_ENABLED=true</code> and a token to read a live tenant.
    </div>
  );
}

function Intro() {
  return (
    <PageIntro>
      A read-only window onto the connected Palantir Foundry tenant — ontologies, object types,
      and a few sample records, served through ORCA&apos;s admin-only integration endpoints.
      ORCA holds no Foundry credentials in the browser and never writes to Foundry here.
    </PageIntro>
  );
}
