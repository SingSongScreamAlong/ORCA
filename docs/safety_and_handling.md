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

## Human review is mandatory

Nothing in ORCA becomes confirmed knowledge without a human decision. Observations
enter a review queue as `proposed`; an analyst with review authority approves, rejects,
or marks them `needs_more_review`. Relationships may only cite **approved** observations.
Every decision is written to an append-only audit log. See
[`analyst_workflow.md`](analyst_workflow.md).
