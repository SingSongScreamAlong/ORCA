import Link from "next/link";
import { ReportPackages } from "@/components/reports/ReportPackages";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/States";
import { PageIntro } from "@/components/ui/PageIntro";
import { getCases, getReportPackages } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ReportsPage() {
  // Report packages are visible to every role that may view approved reports (including
  // partner export viewers), scoped to assigned cases. The case list is only available
  // to roles that may read case material.
  const [packages, cases] = await Promise.all([getReportPackages(), getCases()]);

  return (
    <div className="space-y-6">
      <PageIntro>
        Reports are authored under a case and draw only on approved evidence. A report
        package is an immutable, partner-ready export — a report plus an evidence manifest
        with SHA-256 hashes — that excludes proposed, rejected, and quarantined material and
        never bundles raw evidence files.
      </PageIntro>

      <Card title="Report packages">
        <ReportPackages packages={packages.ok ? packages.data : []} />
      </Card>

      {cases.ok && cases.data.length > 0 && (
        <Card title="Generate a report from a case">
          <ul className="divide-y divide-surface-border">
            {cases.data.map((c) => (
              <li key={c.id} className="flex items-center justify-between py-2.5">
                <span className="text-sm text-ink">{c.title}</span>
                <Link href={`/cases/${c.id}?tab=export`} className="text-sm font-medium">
                  Open export →
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {(!packages.ok || packages.data.length === 0) && !(cases.ok && cases.data.length > 0) && (
        <EmptyState message="No report packages available to you yet." />
      )}
    </div>
  );
}
