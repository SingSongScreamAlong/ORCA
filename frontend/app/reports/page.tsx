import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { BackendNotice, EmptyState } from "@/components/ui/States";
import { PageIntro } from "@/components/ui/PageIntro";
import { getCases } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ReportsPage() {
  const cases = await getCases();

  return (
    <div className="space-y-6">
      <PageIntro>
        Reports are authored under a case and draw only on approved evidence. Open a case and use
        its Draft report tab to generate one — every claim traces back to the observations that
        support it.
      </PageIntro>

      {!cases.ok ? (
        <BackendNotice error={cases.error} status={cases.status} />
      ) : cases.data.length === 0 ? (
        <EmptyState message="No cases yet. Reports are generated within a case." />
      ) : (
        <Card title="Generate a report from a case">
          <ul className="divide-y divide-surface-border">
            {cases.data.map((c) => (
              <li key={c.id} className="flex items-center justify-between py-2.5">
                <span className="text-sm text-ink">{c.title}</span>
                <Link href={`/cases/${c.id}?tab=report`} className="text-sm font-medium">
                  Draft report →
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
