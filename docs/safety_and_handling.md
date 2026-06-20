# Safety & Handling

ORCA is an evidence platform for **lawful, analyst-controlled** intelligence work in
support of anti-trafficking analysis. This document states the boundaries that govern
its use. They are not optional guidance; they define what ORCA is for and what it must
never become. They restate and operationalize [`mission.md`](mission.md).

A visible Safety & Handling page in the application mirrors this document.

## Prohibited uses

ORCA must not be used for any of the following:

- **No hacking.** ORCA is never used to gain unauthorized access to systems, accounts,
  networks, or data.
- **No unauthorized access.** Only lawfully obtained, authorized, or publicly available
  information is recorded.
- **No impersonation.** ORCA is not used to create false personas, sock puppets, or to
  deceive anyone.
- **No vigilantism.** ORCA produces reviewed evidence for authorized analysts. It is
  not a tool for taking action against any person.
- **No direct contact.** ORCA must not be used to contact, message, bait, or otherwise
  engage suspected offenders or victims.
- **No CSAM.** Child sexual abuse material is never stored, uploaded, transmitted, or
  handled in ORCA under any circumstance.

If a proposed feature requires crossing one of these boundaries, the answer is no.

## Urgent or illegal material

If you encounter material indicating imminent harm, or content that is illegal to
possess — including CSAM:

1. **Stop.** Do not download, store, screenshot, upload, or forward it within ORCA.
2. **Do not handle it.** ORCA is not a repository for illegal material and has no
   workflow for it.
3. **Escalate immediately** through your organization's authorized reporting channel
   and the appropriate authorities (for example, in the United States, the NCMEC
   CyberTipline and law enforcement).

ORCA is **not** a reporting authority and is **not** monitored for emergencies. Report
urgent or illegal material through authorized channels.

## The Evidence Locker (v0.3)

The Evidence Locker stores **metadata, lawful files, and partner-approved workflows
only**. Before adding any evidence item, the intake form requires acknowledgement that:

- **Do not upload or store CSAM.**
- **Do not upload illegally obtained material.**
- **Do not store private/personal material unless authorized.**
- **Urgent or illegal content must be reported through authorized channels.**

How the locker keeps evidence safe and accountable:

- **Integrity.** When lawful bytes are provided, ORCA computes a SHA-256 and stores the
  bytes content-addressed by that hash. A *verify* re-hashes the bytes and reports any
  mismatch. Partner files may instead carry a precomputed hash (then ORCA records but
  cannot re-verify it).
- **Provenance.** Every item is attributed to a `Source`, carries an `access_method`,
  and records who created it and when.
- **Scope.** An item belongs to exactly one case and may only be linked to an
  observation **in the same case** — evidence cannot be linked across unrelated cases.
- **Chain-of-custody audit.** Every create, link, status change (approve / reject /
  needs_more_review / **quarantine**), and verify is written to the append-only audit
  log.
- **Quarantine.** An item that must be isolated pending a handling decision can be
  marked `quarantined`; quarantined and rejected evidence is excluded from reports.

## Manual file upload (v0.7)

v0.7 adds real manual upload of lawful files to the Evidence Locker (see
[`v0.7_evidence_file_upload.md`](v0.7_evidence_file_upload.md)). It is upload/storage
only — no collection, scraping, or external fetching.

- **Acknowledgement is mandatory.** Every upload requires the analyst to confirm the
  boundaries on this page; the backend rejects an upload that is not acknowledged.
- **Safe-by-default policy.** Executable/script types are refused outright (never
  stored); unknown types are stored **quarantined** pending review; only allow-listed
  types are accepted. Oversize files are rejected before storage.
- **Hashed and content-addressed.** Bytes are stored keyed by their SHA-256 and can be
  re-verified; ORCA never executes, decodes, renders, or transmits content.
- **Access-controlled.** Upload requires active, mutating case membership; raw bytes are
  restricted to administrators and mutating roles (case manager / analyst / reviewer).
  Viewers see metadata only (unless a deployment opts them in for approved evidence); the
  partner export viewer reaches neither raw bytes nor raw metadata. Every upload,
  download, and verification is audited.

## Legal & handling flags (v0.2 placeholders)

Every observation carries lightweight legal/handling metadata so provenance and care
are explicit and reviewable. These are **governance placeholders** — they record
analyst judgement; they do not implement any collection capability.

| Field                   | Meaning                                                         |
| ----------------------- | -------------------------------------------------------------- |
| `lawful_basis`          | Why the material was lawfully obtained (e.g. "publicly available information"). |
| `requires_legal_review` | Flags an item that must be reviewed by legal before it is relied upon. |
| `sensitive`             | Marks material requiring careful handling.                     |
| `notes`                 | Free-text handling notes.                                      |

A case also carries an optional `legal_notes` field for case-level handling context.

These fields appear on the intake form, on the case observations view, and are
summarized in generated report drafts.

## What v0.2 deliberately does not do

Consistent with the milestone scope, ORCA v0.2 does **not** implement:

- scraping or automated collection,
- dark-web or covert collection,
- autonomous "hunting",
- or any external integrations.

Collection ("Hunting Grounds") remains interface-only (see
[`architecture.md`](architecture.md) and `backend/app/collection`). When collection is
built, collectors will be ordinary, audited producers of observations and evidence —
bound by every boundary on this page.

## Access is enforced by the system (v0.4)

Authorization is no longer a UI convention — it is enforced on every endpoint by
role-based access control (see [`v0.4_auth_rbac.md`](v0.4_auth_rbac.md)). This hardens
the safety posture:

- **Least privilege.** Viewers read but cannot mutate; analysts propose but cannot
  approve; only reviewers (and admins) decide.
- **Separation of duties.** No one may approve their own proposed intelligence; an
  admin override is required and is recorded as a distinct audit event.
- **Partner isolation.** `partner_export_viewer` can access **only** published report
  packages — never raw evidence or case material.
- **Accountability.** Every privileged action is attributed to an authenticated user in
  the append-only audit log.

## Need-to-know is enforced per case (v0.6)

RBAC bounds what a *kind* of user may do; v0.6 adds **case membership** so analysts see
only the cases they are assigned to (see [`v0.6_case_membership.md`](v0.6_case_membership.md)).

- **Least exposure.** A non-administrator must hold an active membership in a case to
  open, mutate, graph, review, or export it; an unassigned user sees nothing — not even
  whether the case exists. Denials are generic, so the system cannot be used to
  enumerate cases or leak titles, counts, or evidence metadata.
- **Per-case roles.** The same person can be a reviewer on one case and only a viewer on
  another; the case role, not just the global role, governs what they may do there.
- **Auditable roster.** Adding, re-roling, or revoking a member is an audited action,
  keeping access to sensitive cases reviewable after the fact.

## Partner export packages (v0.8)

Report packages (see [`v0.8_report_package_export.md`](v0.8_report_package_export.md)) are
the sanctioned way to share findings with partners. They are export-only and conservative
by design:

- **Approved material only.** Proposed, rejected, needs-more-review, and quarantined
  observations and evidence are excluded from every package.
- **No raw files.** Evidence is represented by metadata and SHA-256 hashes; raw evidence
  bytes, the case audit log, and the relationship graph are never bundled or exposed to
  the partner export viewer.
- **Scoped and audited.** A partner sees packages only for cases they are assigned to;
  generation and every download are recorded in the append-only audit log.

## AI assistance is propose-only (v1.0)

The Analyst Copilot ([`v1.0_aip_assisted_analyst_copilot.md`](v1.0_aip_assisted_analyst_copilot.md))
assists analysts without ever deciding for them:

- **Proposed only.** Every AI result is a suggestion/draft/candidate marked
  `generated_by_ai` and `requires_human_review`; it never becomes authoritative case
  material automatically, and the Copilot has no write path into the record.
- **Approved material only.** The Copilot reasons over approved observations, evidence, and
  relationships the caller may read — never proposed/rejected/quarantined material, and
  never anything outside the caller's case membership. Partner export viewers cannot use it.
- **Forbidden uses are not implemented:** no autonomous collection, scraping, dark-web
  browsing, face recognition/matching, victim/offender targeting, identity claims without
  review, direct-contact suggestions, law-enforcement conclusions, risk scoring of real
  people, automated report approval, or AI claims in partner exports.
- **Local and credential-free** by default (deterministic mock provider); audited on every
  request. AI proposes; analysts decide.

## Human review is mandatory

Nothing in ORCA becomes confirmed knowledge without a human decision. Observations
enter a review queue as `proposed`; an analyst with review authority approves, rejects,
or marks them `needs_more_review`. Relationships may only cite **approved** observations.
Every decision is written to an append-only audit log. See
[`analyst_workflow.md`](analyst_workflow.md).
