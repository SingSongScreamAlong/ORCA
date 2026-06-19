# Roadmap

The roadmap is phased so that the foundation — evidence, observations, and
relationships — is solid before anything is built on top of it. Each phase produces
something an analyst can use, and no phase weakens the principles in
[`mission.md`](mission.md).

Phases are ordered by dependency, not by date. Dates are intentionally omitted; the
sequence is the commitment.

## Phase 0 — Skeleton (this repository)

**Goal:** establish the structure, the data model, and the contracts.

- [x] Repository structure and documentation.
- [x] Ontology v0.1 (narrative + machine-readable schemas).
- [x] Backend skeleton: FastAPI app, layered structure, placeholder endpoints.
- [x] Database structure: PostgreSQL schema and migration scaffolding, Neo4j
      constraints.
- [x] Frontend skeleton: Next.js application with all primary screens, including the
      review queue.
- [x] Infrastructure: local orchestration for PostgreSQL and Neo4j.
- [x] Hunting Grounds defined as interfaces only.

The skeleton is deliberately honest: endpoints and screens exist and are wired to the
data model, but business logic is minimal and clearly marked.

> **v0.6 status.** **Case Membership & Authorization Scoping** completes the access-control
> work in Phases 1 and 6: need-to-know on top of RBAC. A non-admin must hold an active
> membership in a case to see or act on it, and a per-case role decides what they may do
> there; case listing, detail, observations, evidence, relationships, graph, audit,
> review queue, and report/export access are all scoped. A membership roster with an
> audited add/role-change/deactivate lifecycle is exposed, and denials are generic 403s
> that never reveal a case's existence or contents. See
> [`v0.6_case_membership.md`](v0.6_case_membership.md).
>
> **v0.5 status.** **Relationship Graph & Discovery** begins Phase 4: graph queries over
> the approved-relationship record — entity neighbourhoods, case subgraphs, and shortest
> paths — exposed as RBAC-gated read endpoints and a calm node-link Graph tab. Queries
> read the authoritative relational record; the Neo4j projection mirrors the same edges
> when enabled. Assistive proposals already route through the review queue (v0.2).
> See [`v0.5_graph_discovery.md`](v0.5_graph_discovery.md).
>
> **v0.4 status.** **Auth/RBAC + Workspace Hardening** delivers the access-control parts
> of Phase 1 and Phase 6: real authenticated identities, six roles with a capability
> matrix enforced on every endpoint (403 on denial, 401 on unknown identity), separation
> of duties on approvals with an explicit audited admin override, case membership /
> assignment, report publishing for partner export, and demo users per role. See
> [`v0.4_auth_rbac.md`](v0.4_auth_rbac.md).
>
> **v0.3 status.** The **Evidence Locker + Integrity Layer** advances Phase 1's
> evidence work: a rich, case-scoped `EvidenceItem` with source attribution and file
> metadata, **SHA-256 hashing and on-demand verification** over a content store,
> a `quarantined` status, chain-of-custody audit events for create / link / decide /
> verify, the cross-case linking guard, and report citations of approved evidence.
> No scraping, dark-web collection, autonomous hunting, face search, or
> offender/victim targeting — and no CSAM storage/handling, by design.
>
> **v0.2 status.** The **Analyst Loop MVP** delivers a vertical slice across Phases 1–3:
> case creation, observation intake with source + handling metadata, the observation
> review queue (approve / reject / needs_more_review), relationships that may only cite
> approved observations, the case timeline, the case-scoped append-only audit log, and
> a draft-report generator that uses approved evidence only. A production PostgreSQL
> persistence path (SQLAlchemy unit of work + Alembic migration) is implemented and
> integration-tested. Evidence hashing/integrity, real authentication, and the Neo4j
> projection remain to complete the phases below.

## Phase 1 — Evidence and observations

**Goal:** record and preserve, end to end.

- Evidence ingestion with SHA-256 hashing and immutable storage.
- Integrity verification on read.
- Observation create/read with source attribution and evidence linking.
- Entity resolution (deduplication by type + canonical value).
- Audit log writing for all consequential actions.
- Authentication and role-based access (analyst / reviewer / admin).

**Exit criterion:** an analyst can preserve evidence, record an observation against
it, and re-verify the evidence later.

## Phase 2 — Relationships and review

**Goal:** discover links and route them through human review.

- Relationship model with mandatory supporting observations.
- Neo4j projection kept in sync with PostgreSQL.
- System-proposed relationships from co-occurrence (shared phone, image, location,
  account, appears-with).
- The review queue: rationale, evidence, confidence, and Approve / Reject / Needs
  review actions.
- Status lifecycle and audit entries for every decision.

**Exit criterion:** a proposed relationship is visible in the review queue with its
rationale and evidence, and an analyst's decision is recorded and reflected in the
graph.

## Phase 3 — Clusters, cases, and reports

**Goal:** let analysts build and communicate findings.

- Clustering of confirmed relationships and their entities/observations.
- Cases as curated views; reference (not ownership) of underlying objects.
- Report authoring with citations back to observations and evidence.
- Case and report lifecycle (`open/active/closed`, `draft/in_review/final`).

**Exit criterion:** an analyst can assemble a case from confirmed evidence and produce
a report whose every claim cites its support.

## Phase 4 — Graph analytics and assistance

**Goal:** help analysts see patterns, without asserting conclusions.

- Graph queries and visualization (paths, neighborhoods, cluster size).
- Assistive proposals (candidate clusters, suggested entity merges) — always routed
  through review.
- Explainability surfaced for every proposal.

**Exit criterion:** the system surfaces non-obvious candidate patterns, each with an
explanation, and none of them bypasses review.

## Phase 5 — Hunting Grounds (collection)

**Goal:** implement collection behind the interfaces defined in Phase 0.

- Monitoring and archiving of sources.
- Entity extraction from collected material.
- Evidence preservation at capture.
- Collectors act as ordinary producers of observations and evidence — no privileged
  path that bypasses review or audit.

**Exit criterion:** a collector can preserve evidence and propose observations through
the same audited, reviewed path an analyst uses.

## Phase 6 — Hardening and operations

**Goal:** make it dependable.

- Production deployment topology and infrastructure-as-code.
- Encryption at rest, secret management, backup and restore drills.
- Performance and scale work on the graph projection.
- Security review and access-control audits.

## Non-goals

The following are out of scope across all phases, by mission:

- Unauthorized access to systems or accounts.
- Real-time or covert tracking of individuals.
- Detection evasion.
- Any automated process that produces a finding about a person.

If a proposed feature requires one of these, the answer is no — regardless of phase.
