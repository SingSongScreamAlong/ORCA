import { Card } from "@/components/ui/Card";
import { PageIntro } from "@/components/ui/PageIntro";

const PROHIBITED = [
  ["No hacking", "ORCA is not used to gain unauthorized access to systems, accounts, or data."],
  ["No unauthorized access", "Only lawfully obtained, authorized, or publicly available information is recorded."],
  ["No impersonation", "ORCA is not used to create false personas or deceive."],
  ["No vigilantism", "ORCA produces evidence for authorized analysts; it is not a tool for taking action against anyone."],
  [
    "No direct contact",
    "Do not use ORCA to contact, message, or engage suspected offenders or victims.",
  ],
  [
    "No CSAM",
    "Child sexual abuse material is never stored, uploaded, or handled in ORCA. If encountered, stop and report it through authorized channels immediately.",
  ],
];

export default function SafetyPage() {
  return (
    <div className="space-y-6">
      <PageIntro>
        ORCA is an evidence platform for lawful, analyst-controlled intelligence work. These
        boundaries are not optional — they define what ORCA is for and what it must never become.
        All conclusions remain human-reviewed.
      </PageIntro>

      <Card title="Prohibited uses">
        <ul className="divide-y divide-surface-border">
          {PROHIBITED.map(([title, body]) => (
            <li key={title} className="flex gap-3 py-3">
              <span className="mt-0.5 select-none text-band-low" aria-hidden>
                ✕
              </span>
              <div>
                <div className="text-sm font-medium text-ink">{title}</div>
                <div className="text-sm text-ink-muted">{body}</div>
              </div>
            </li>
          ))}
        </ul>
      </Card>

      <Card title="Urgent or illegal material">
        <p className="text-sm text-ink-muted">
          If you encounter material indicating imminent harm, or content that is illegal to possess
          (including CSAM), do not download, store, or forward it within ORCA. Stop, preserve only
          what your authorized procedures permit, and escalate immediately through your
          organization&apos;s authorized reporting channel and the appropriate authorities.
        </p>
        <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Report urgent or illegal material through authorized channels. ORCA is not a reporting
          authority and is not monitored for emergencies.
        </div>
      </Card>

      <Card title="The Evidence Locker">
        <p className="text-sm text-ink-muted">
          The Evidence Locker stores metadata, lawful files, and partner-approved workflows only.
          Adding an item requires acknowledging the boundaries above. Evidence is attributed to a
          source, scoped to a single case (and can only link to observations in that case), and
          every create, link, status change, and hash verification is written to the append-only
          audit log. Lawful content is hashed with SHA-256 and can be re-verified; material that
          must be isolated can be <span className="font-medium text-ink">quarantined</span> and is
          then excluded from reports.
        </p>
      </Card>

      <Card title="Handling flags on every observation">
        <p className="text-sm text-ink-muted">
          Each observation carries legal/handling metadata so provenance and care are explicit:
        </p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-ink-muted">
          <li>
            <span className="font-medium text-ink">Lawful basis</span> — a statement of why the
            material was lawfully obtained (e.g. publicly available information).
          </li>
          <li>
            <span className="font-medium text-ink">Flag for legal review</span> — marks an item that
            must be reviewed before it is relied upon.
          </li>
          <li>
            <span className="font-medium text-ink">Sensitive</span> — marks material that requires
            careful handling.
          </li>
        </ul>
        <p className="mt-4 text-xs text-ink-faint">
          These are governance placeholders in v0.2. ORCA does not implement collection of sensitive
          material; see the mission and security documentation.
        </p>
      </Card>
    </div>
  );
}
