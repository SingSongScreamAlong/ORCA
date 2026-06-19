import { IntakeForm } from "@/components/intake/IntakeForm";
import { BackendNotice } from "@/components/ui/States";
import { PageIntro } from "@/components/ui/PageIntro";
import { getCases } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function IntakePage({
  searchParams,
}: {
  searchParams: { case?: string };
}) {
  const cases = await getCases();
  if (!cases.ok) {
    return (
      <div className="space-y-6">
        <Intro />
        <BackendNotice error={cases.error} status={cases.status} />
      </div>
    );
  }
  return (
    <div className="space-y-6">
      <Intro />
      <IntakeForm cases={cases.data} defaultCaseId={searchParams.case} />
    </div>
  );
}

function Intro() {
  return (
    <PageIntro>
      Record a single observation — a fact, attributed to a source, supported by evidence.
      Every observation enters the review queue and is only usable once an analyst approves it.
    </PageIntro>
  );
}
