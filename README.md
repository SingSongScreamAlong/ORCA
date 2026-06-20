# ORCA

**O**bservation · **R**econnaissance · **C**ollection · **A**nalysis

ORCA is an evidence platform for intelligence analysts. It preserves observations,
discovers relationships between entities, and maintains an institutional memory of
those relationships over time — so that analysts can identify meaningful,
evidence-supported patterns that would otherwise remain unseen.

The initial use case is open-source intelligence (OSINT) analysis in support of
anti-trafficking work.

---

## What ORCA is

- An **observation** platform — observations are recorded, attributed, and preserved.
- An **evidence** platform — every claim traces back to a preserved artifact.
- A **relationship discovery** platform — entities and the links between them are
  first-class, and they persist beyond any single case.
- An **analyst workflow** platform — the software proposes; analysts decide.

## What ORCA is not

- Not a hacking platform.
- Not a surveillance platform.
- Not an undercover platform.
- Not a law-enforcement platform.
- Not an automated accusation engine.

**All conclusions remain human-reviewed.** ORCA surfaces candidates and supporting
evidence. It never asserts a finding on its own.

---

## Core principles

1. Observation is the atomic unit of truth.
2. Every relationship must be traceable to evidence.
3. Every assessment must be explainable.
4. AI proposes.
5. Analysts decide.
6. Evidence is more important than conclusions.
7. Relationships persist longer than cases.
8. Cases are views of evidence, not the source of truth.

These principles are not decoration. They are encoded in the data model (see
[`docs/ontology_v0.1.md`](docs/ontology_v0.1.md)) and in the review workflow
(see [`docs/analyst_workflow.md`](docs/analyst_workflow.md)).

---

## Repository layout

| Path              | Contents                                                            |
| ----------------- | ------------------------------------------------------------------- |
| `docs/`           | Mission, architecture, roadmap, security, workflow, and ontology.   |
| `ontology/`       | Machine-readable definitions of every object type and relationship. |
| `backend/`        | FastAPI service, data models, services, repositories, and workers.  |
| `frontend/`       | Next.js analyst application (evidence-first, information dense).     |
| `infrastructure/` | Local orchestration (PostgreSQL, Neo4j) and environment templates.  |
| `foundry/`        | Exported ORCA → Palantir Foundry ontology mapping (JSON spec).       |
| `tests/`          | Structure and contract tests across the repository.                 |

## Documentation

| Document                                             | Purpose                                                |
| ---------------------------------------------------- | ------------------------------------------------------ |
| [Mission](docs/mission.md)                           | Why ORCA exists and the boundaries it will not cross.  |
| [Architecture](docs/architecture.md)                 | System shape, data stores, and request flow.           |
| [Ontology v0.1](docs/ontology_v0.1.md)               | The object model: observations, entities, relationships.|
| [Analyst workflow](docs/analyst_workflow.md)         | How an analyst moves from observation to report.       |
| [Security](docs/security.md)                         | Access control, evidence integrity, audit, encryption. |
| [Safety & Handling](docs/safety_and_handling.md)     | Boundaries: lawful, analyst-controlled, human-reviewed.|
| [v0.2 Analyst Loop](docs/v0.2_analyst_loop.md)       | The end-to-end intake → review → report loop.          |
| [v0.3 Evidence Locker](docs/v0.3_evidence_locker.md) | Evidence items, SHA-256 integrity, chain-of-custody.   |
| [v0.4 Auth/RBAC](docs/v0.4_auth_rbac.md)             | Roles, capability matrix, separation of duties.        |
| [v0.5 Graph & Discovery](docs/v0.5_graph_discovery.md)| Neighbourhoods, case subgraphs, shortest paths.        |
| [v0.6 Case Membership](docs/v0.6_case_membership.md) | Per-case authorization, need-to-know, membership roster.|
| [v0.7 Evidence Upload](docs/v0.7_evidence_file_upload.md)| Manual file upload, hashing, upload policy, scoped download.|
| [v0.8 Report Package Export](docs/v0.8_report_package_export.md)| Partner-ready report + evidence manifest, hashes, scoped export.|
| [v0.9 Foundry Mapping](docs/v0.9_palantir_foundry_mapping.md)| ORCA → Palantir Foundry ontology mapping (spec + local scaffolding).|
| [Roadmap](docs/roadmap.md)                            | Phased delivery, starting from this skeleton.          |

---

## Status

- **v0.1 — skeleton.** Structure, data model, API surface, and analyst screens.
- **v0.2 — Analyst Loop MVP.** One complete, auditable loop: case → observation
  intake → review queue → approval → relationship (citing approved evidence) →
  timeline/audit → draft report. PostgreSQL persistence path is implemented and
  integration-tested. See [`docs/v0.2_analyst_loop.md`](docs/v0.2_analyst_loop.md).
- **v0.3 — Evidence Locker + Integrity Layer.** Case-scoped evidence items with source
  attribution, file metadata, **SHA-256 hashing + verification**, quarantine,
  chain-of-custody audit events, and report citations. See
  [`docs/v0.3_evidence_locker.md`](docs/v0.3_evidence_locker.md).
- **v0.4 — Auth/RBAC + Workspace Hardening.** Real authenticated identities,
  **six roles** with a capability matrix enforced on every endpoint (403/401),
  **separation of duties** on approvals with an audited admin override, case
  membership/assignment, and report publishing for partner export. See
  [`docs/v0.4_auth_rbac.md`](docs/v0.4_auth_rbac.md).
- **v0.5 — Relationship Graph & Discovery.** Graph queries over approved
  relationships — entity neighbourhoods, case subgraphs, and shortest paths — with a
  calm node-link Graph tab. See [`docs/v0.5_graph_discovery.md`](docs/v0.5_graph_discovery.md).
- **v0.6 — Case Membership & Authorization Scoping.** Need-to-know access on
  top of RBAC: non-admins see and act on only the cases they are assigned to, scoped by a
  per-case role; a membership roster with an audited lifecycle; and generic 403s that
  never leak a case's existence or contents. See
  [`docs/v0.6_case_membership.md`](docs/v0.6_case_membership.md).
- **v0.7 — Evidence File Upload + Storage Hardening.** Real manual upload of
  lawful files into the Evidence Locker: SHA-256 hashing + verification, a safe-by-default
  upload policy (reject executables, quarantine unknown types, size cap), role- and
  case-scoped raw-byte download, a mandatory safety acknowledgement, and audited
  upload/download. Upload/storage only — no collection. See
  [`docs/v0.7_evidence_file_upload.md`](docs/v0.7_evidence_file_upload.md).
- **v0.8 — Report Package Export.** Partner-ready export packages built from
  **approved material only**: a Markdown report plus a JSON evidence manifest with
  SHA-256 hashes (and an optional ZIP). Generation is role-gated; partner export viewers
  can view/download packages for assigned cases but never raw evidence, the graph, or the
  audit log; proposed/rejected/quarantined material is excluded; generation and downloads
  are audited. See [`docs/v0.8_report_package_export.md`](docs/v0.8_report_package_export.md).
- **v0.9 — Palantir Foundry Ontology Mapping (current).** A Foundry-ready ontology
  **specification and local mapping module** (`backend/app/foundry_mapping/`, exported to
  `foundry/*.json`) describing ORCA's objects, links, actions, and permissions as Foundry
  concepts — **mapping/spec only, no live Palantir calls or sync**. The mapping preserves
  every ORCA invariant (approved-only reports/graph, need-to-know membership, no raw
  evidence for partner export viewers, audited actions, no CSAM handling). See
  [`docs/v0.9_palantir_foundry_mapping.md`](docs/v0.9_palantir_foundry_mapping.md).

Collection ("Hunting Grounds") remains an interface only — no collection logic, no
scraping, no autonomous hunting. ORCA stays evidence-first, lawful, and analyst-controlled
(see [`docs/safety_and_handling.md`](docs/safety_and_handling.md)).

## Getting started

```bash
# Bring up PostgreSQL and Neo4j locally
cd infrastructure
cp env/.env.example .env
docker compose up -d postgres neo4j

# Backend (FastAPI)
cd ../backend
cp .env.example .env
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Frontend (Next.js)
cd ../frontend
cp .env.example .env.local
npm install
npm run dev
```

See [`backend/README.md`](backend/README.md) and
[`frontend/README.md`](frontend/README.md) for details.

## License

See [`LICENSE`](LICENSE). Use of ORCA is subject to the ethical boundaries described
in the [mission](docs/mission.md).
