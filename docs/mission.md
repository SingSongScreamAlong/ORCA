# Mission

## Purpose

ORCA exists to preserve observations, discover relationships, and maintain
institutional intelligence memory so that analysts can identify meaningful,
evidence-supported patterns that would otherwise remain unseen.

The initial use case is open-source intelligence (OSINT) analysis in support of
anti-trafficking work. The data model and workflow are general; the first
deployment is specific.

## The problem ORCA addresses

Analytic work loses information in three predictable ways:

1. **Observations are not preserved.** An analyst notices that two advertisements
   share a phone number, acts on it, and the underlying artifact disappears. The
   conclusion outlives the evidence, and the evidence can no longer be re-examined.

2. **Relationships die with the case.** A link discovered in one investigation is
   not available to the next. Institutional knowledge resets every time a case
   closes.

3. **Assessments are not explainable.** A judgment is recorded without the chain of
   observations that produced it, so it cannot be reviewed, challenged, or trusted
   later.

ORCA is built to prevent all three.

## What ORCA optimizes for

- **Durability of evidence.** The preserved artifact is the point. Conclusions are
  derived and revisable; evidence is retained and verifiable.
- **Traceability.** Every relationship references the observations that support it.
  Every observation references the evidence that supports it.
- **Explainability.** Anything the system surfaces for review is accompanied by the
  reason it was surfaced and the evidence behind it.
- **Continuity.** Entities and relationships persist across cases. A case is a lens,
  not a container.

## What ORCA is not

ORCA is **not**:

- **A hacking platform.** It does not gain unauthorized access to systems or data.
- **A surveillance platform.** It does not track people in real time or operate
  covert monitoring.
- **An undercover platform.** It does not support deception operations or false
  personas.
- **A law-enforcement platform.** It makes no arrests, files no charges, and is not
  a system of record for any enforcement action.
- **An automated accusation engine.** It never asserts that a person is guilty of
  anything. It surfaces candidate relationships and the evidence behind them.

These are boundaries, not disclaimers. Features that would require crossing them are
out of scope.

## The human is the decision-maker

ORCA proposes; the analyst decides. The software can:

- preserve an observation,
- extract candidate entities,
- propose a relationship between entities,
- group entities and observations into a candidate cluster,
- and explain why each of these was surfaced.

The software cannot:

- confirm a relationship,
- assert an identity,
- or draw a conclusion.

Those actions belong to a person, are recorded against that person, and are
auditable. This division is enforced by the data model: system-proposed objects
carry an `origin` of `system_proposed` and a `status` of `proposed` until an analyst
acts on them. See [`analyst_workflow.md`](analyst_workflow.md).

## Ethical posture

The subject matter is sensitive and the cost of error is high. ORCA is designed so
that:

- a mistaken conclusion can always be traced back to the evidence and the person who
  drew it,
- evidence cannot be silently altered (see [`security.md`](security.md)),
- and no automated process produces a finding about a person.

When in doubt, ORCA preserves more context and asserts less.
