import { Card } from "@/components/ui/Card";
import { PageIntro } from "@/components/ui/PageIntro";

export default function CasesPage() {
  return (
    <div className="space-y-6">
      <PageIntro>
        Cases are analyst work products — curated views over observations, entities,
        clusters, and reports. A case is a lens, not a container: it references evidence
        and never owns it, so closing a case never deletes the underlying record.
      </PageIntro>

      <Card title="Cases arrive in Phase 3">
        <p className="text-sm text-ink-muted">
          The case workspace is built on top of confirmed evidence and relationships. It
          is scheduled after the evidence, observation, relationship, and review surfaces
          are complete, so that a case is always assembled from reviewed material.
        </p>
        <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-ink-muted">
          <li>Assemble a case as a view over selected observations, entities, and clusters.</li>
          <li>Track case status from open through closed without touching the evidence.</li>
          <li>Author reports under a case, each citing its supporting observations.</li>
        </ul>
        <p className="mt-4 text-xs text-ink-faint">
          See the roadmap (<span className="mono">docs/roadmap.md</span>, Phase 3) for the
          full plan.
        </p>
      </Card>
    </div>
  );
}
