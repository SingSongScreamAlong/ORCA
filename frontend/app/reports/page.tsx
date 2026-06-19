import { Card } from "@/components/ui/Card";
import { PageIntro } from "@/components/ui/PageIntro";

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <PageIntro>
        Reports are the human-readable analytic products authored under a case. A report
        cites the observations and evidence it rests on, so every claim can be verified —
        and it states only what the evidence supports.
      </PageIntro>

      <Card title="Reports arrive in Phase 3">
        <p className="text-sm text-ink-muted">
          Report authoring depends on cases, which depend on confirmed evidence. Reports
          move through draft, in&nbsp;review, and final, and each claim links back to the
          observations that support it.
        </p>
        <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-ink-muted">
          <li>Author a report under a case, in markdown.</li>
          <li>Cite supporting observations and evidence inline.</li>
          <li>Move through a draft → in&nbsp;review → final lifecycle.</li>
        </ul>
        <p className="mt-4 text-xs text-ink-faint">
          See the roadmap (<span className="mono">docs/roadmap.md</span>, Phase 3) for the
          full plan.
        </p>
      </Card>
    </div>
  );
}
