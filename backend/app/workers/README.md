# Workers

Background tasks that assist analysts. The defining rule for everything here:

> A worker proposes. It never confirms.

Every artifact a worker produces — a candidate relationship, a candidate cluster, a
flagged observation — is created with `origin = system_proposed` and `status =
proposed`, and is placed in the review queue. A worker has no privileged path to the
confirmed graph; it goes through the same review and audit as an analyst's proposal.

## In this skeleton

- `tasks.py` — a minimal task registry. No scheduler is wired up; tasks are plain
  callables you can invoke directly.
- `relationship_proposer.py` — an illustrative worker. It scans observations for
  entities that share a phone number and proposes `shared_phone` relationships,
  each routed to the review queue with a human-readable rationale.

## Future workers (interfaces in `app/collection`)

Collection ("Hunting Grounds") will add workers for monitoring, archiving, entity
extraction, and evidence preservation. Those are defined as interfaces only in
`app/collection/interfaces.py` — no collection logic is implemented here.
