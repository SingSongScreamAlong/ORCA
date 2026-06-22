# ORCA — Palantir / Foundry Pitch Notes

Framing notes for a technical conversation with Palantir about running ORCA on Foundry.
These are talking points, not commitments; the concrete mapping is in
[`v0.9_palantir_foundry_mapping.md`](v0.9_palantir_foundry_mapping.md) and the exported
spec in `foundry/*.json`.

## What ORCA is (today)

A lawful, auditable **case-intelligence workspace** for OSINT analysis in support of
anti-trafficking work. It runs locally end to end: a FastAPI backend (in-memory or
PostgreSQL), a Next.js analyst UI, and 151 passing backend tests. Its defining property is
discipline, not breadth: **AI proposes, analysts decide**; evidence is hash-verifiable and
case-scoped; access is need-to-know; every consequential action is audited.

## Current local architecture

- **Domain:** cases, sources, observations, evidence items, entities, relationships,
  review items, reports, report packages, audit events, users, case memberships.
- **Layering:** API (routes + guards) → services (invariants) → repositories (unit of
  work) → store (in-memory or PostgreSQL). Authorization is enforced at the boundary and
  re-checked in services.
- **Integrity:** SHA-256 content-addressed evidence with on-read verification.
- **Access:** six global roles + per-case roles (need-to-know); separation of duties on
  approvals; partner export viewers limited to approved packages.
- **Audit:** append-only, attributable, no update/delete path.

## How it maps to the Foundry Ontology

The v0.9 mapping (already exported) expresses ORCA as Foundry concepts:

- **13 object types** (`OrcaCase`, `OrcaObservation`, `OrcaEvidenceItem`, `OrcaEntity`,
  `OrcaRelationship`, `OrcaReviewDecision`, `OrcaTask`, `OrcaReport`, `OrcaReportPackage`,
  `OrcaAuditEvent`, `OrcaUser`, `OrcaCaseMembership`, `OrcaSource`).
- **19 link types** mirroring ORCA's enforced relationships (containment, support,
  citation, review-decision, audit) — entity-to-entity traversal only over **approved**
  relationships.
- **20 action types** mirroring ORCA's audited workflows, each with its RBAC + case-role
  gate and the invariant it preserves.
- **Permissions derived from ORCA's real RBAC** so the spec cannot drift from enforcement.

ORCA would remain the **system of record and authorization authority**; Foundry actions
call back into ORCA's services so RBAC, membership, separation of duties, and audit still
apply (one-directional, audited backfill — not the live sync the prototype forbids).

> **v1.1–v1.2 connection work.** ORCA includes read-only connection plumbing
> (`backend/app/foundry/`): a config shape, a client abstraction, a deterministic mock
> client, and a secret-free health check (`python -m app.foundry.health`). v1.2 adds a real,
> **read-only REST connector** (`RestFoundryClient`, httpx) that authenticates via OAuth2
> client-credentials or a bearer token and calls Foundry's documented v2 ontology endpoints
> (`GET /api/v2/ontologies` as the connectivity proof; object-type/object reads on demand).
> It is disabled by default, never tested against a live tenant (an injected mock transport),
> and its first real call against the ORCA tenant is a deliberate, operator-run manual step —
> the natural seam to validate scopes/paths and then wire pilot reads. An OSDK path remains
> selectable (`ORCA_FOUNDRY_CLIENT=sdk`). See
> [`v1.2_foundry_rest_connector.md`](v1.2_foundry_rest_connector.md) and
> [`v1.1_foundry_connection_spike.md`](v1.1_foundry_connection_spike.md).

## Why AIP is propose-only

The mission rule is non-negotiable: AI never produces an authoritative finding about a
person. v1.0's Copilot already implements the propose-only contract locally behind an
`AiProvider` seam — an AIP-backed provider slots in without changing any boundary. Allowed
AIP uses: summarise approved material, suggest candidate entities/relationships, draft
report language from approved observations, flag missing citations / unsupported claims,
surface review gaps. Every output enters the human review queue.

## Why auditability and case membership matter

This domain is sensitive and the cost of an unexplained or over-broad record is high.
Need-to-know case membership (with non-leaking 403s) and an append-only audit log are what
make ORCA *defensible* — every confirmed relationship traces to the person who approved it
and the evidence they saw, and access to sensitive cases is reviewable after the fact.
These are exactly the properties a Foundry deployment must preserve, and the mapping is
built to do so (object/property security + action gates).

## What access / help would be needed from Palantir

- A **development Foundry tenant** to publish the ontology and generate an OSDK.
- Guidance on mapping ORCA's per-case need-to-know and **non-leakage** onto Foundry's
  security primitives (Markings / Restricted Views vs. application-level checks).
- AIP access (if/when) to evaluate a real propose-only provider behind the existing seam.
- Patterns for content-addressed evidence + hash verification within Foundry.
- Security-review partnership on the boundaries in [`threat_model.md`](threat_model.md).

## What a Foundry pilot would test

1. Publish the exported ontology; backfill demo objects from ORCA (audited, one-way).
2. Stand up read views (case workspace, review queue, graph, packages) with object/property
   security matching the ORCA permission mapping.
3. Wire a few actions (create observation, review decision, generate package) through to
   ORCA's services and confirm RBAC + membership + audit still hold.
4. Prove need-to-know and partner isolation in Foundry's security model.
5. (Optional) Evaluate an AIP propose-only provider against the v1.0 Copilot contract.

## Boundaries we will not cross

No offensive collection, scraping, dark-web browsing, face matching, offender/victim
targeting, bulk monitoring, direct contact, autonomous AI conclusions, or CSAM handling —
on any platform. See [`mission.md`](mission.md) and [`safety_and_handling.md`](safety_and_handling.md).
