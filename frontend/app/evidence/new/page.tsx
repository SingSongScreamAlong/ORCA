import { EvidenceIntakeForm } from "@/components/evidence/EvidenceIntakeForm";
import { BackendNotice, EmptyState } from "@/components/ui/States";
import { PageIntro } from "@/components/ui/PageIntro";
import { getCaseObservations, getCases, getSources } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function NewEvidencePage({
  searchParams,
}: {
  searchParams: { case?: string };
}) {
  const [cases, sources] = await Promise.all([getCases(), getSources()]);
  const observations = searchParams.case ? await getCaseObservations(searchParams.case) : null;

  if (!cases.ok || !sources.ok) {
    return (
      <div className="space-y-6">
        <Intro />
        <BackendNotice error={(!cases.ok && cases.error) || (!sources.ok && sources.error) || ""} />
      </div>
    );
  }
  if (cases.data.length === 0 || sources.data.length === 0) {
    return (
      <div className="space-y-6">
        <Intro />
        <EmptyState message="Evidence needs a case and a source. Create a case (and intake an observation) first." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Intro />
      <EvidenceIntakeForm
        cases={cases.data}
        sources={sources.data}
        observations={observations && observations.ok ? observations.data : []}
        defaultCaseId={searchParams.case}
      />
    </div>
  );
}

function Intro() {
  return (
    <PageIntro>
      Record an evidence item: its metadata, source, and — for lawful content — a SHA-256 integrity
      hash. Evidence is created as proposed and decided in the case&apos;s evidence locker.
    </PageIntro>
  );
}
