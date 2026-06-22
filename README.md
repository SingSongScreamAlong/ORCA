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

## Capabilities at v1.0

- **Analyst loop** — case → observation intake → review queue (approve / reject /
  needs-more-review) → relationship (citing approved observations) → timeline → draft report.
- **Evidence locker** — case-scoped evidence with source attribution, **SHA-256 hashing +
  on-read verification**, quarantine, and chain-of-custody audit.
- **Manual file upload** — lawful files hashed and content-addressed, with a safe-by-default
  policy (reject executables, quarantine unknown types, size cap) and role/case-scoped
  raw-byte download.
- **Auth / RBAC** — six roles with a capability matrix on every endpoint (403/401), and
  **separation of duties** on approvals with an audited admin override.
- **Case membership** — need-to-know: non-admins act only on assigned cases, scoped by a
  per-case role; denials are generic 403s that never reveal a case's existence.
- **Relationship graph** — neighbourhoods, case subgraphs, and shortest paths over
  **approved** relationships only.
- **Report package export** — partner-ready Markdown report + JSON evidence manifest (hashes
  only), approved material only.
- **Foundry mapping** — a Foundry-ready ontology spec exported to `foundry/*.json`
  (mapping only; no live Palantir sync).
- **Analyst Copilot** — local, propose-only AI assistance (summaries, candidate entities /
  relationships, draft sections, citation checks) — every output requires human review.
- **Append-only audit** — every privileged action is recorded and attributable.

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
| [v1.0 Analyst Copilot](docs/v1.0_aip_assisted_analyst_copilot.md)| Local, propose-only AI assistance (AI proposes, analysts decide).|
| [v1.1 Foundry Connection Spike](docs/v1.1_foundry_connection_spike.md)| Read-only Foundry connection scaffolding (mock by default).|
| [v1.2 Foundry REST Connector](docs/v1.2_foundry_rest_connector.md)| Real read-only httpx REST connector to Foundry's v2 API.|
| [v1.3 Foundry Read Endpoints](docs/v1.3_foundry_read_endpoints.md)| Admin-only, read-only Foundry data endpoints in the ORCA API.|
| [v1.4 Foundry Import](docs/v1.4_foundry_import.md)| Admin import of Foundry objects into ORCA as entities (read-only against Foundry).|
| [Foundry connection setup](docs/foundry_connection_setup.md)| Manual procedure to test against a real Foundry tenant.|
| [Demo walkthrough](docs/demo_walkthrough.md)         | End-to-end demo path across every v1.0 capability.     |
| [Threat model](docs/threat_model.md)                 | Threats, mitigations, and non-goals.                   |
| [Known limitations](docs/known_limitations.md)       | What v1.0 is deliberately not (yet).                   |
| [Palantir pitch notes](docs/palantir_pitch_notes.md) | Foundry/AIP mapping and what a pilot would test.       |
| [Release notes v1.0](docs/release_notes_v1.0.md)     | Summary of v0.1 → v1.0.                                |
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
- **v0.9 — Palantir Foundry Ontology Mapping.** A Foundry-ready ontology
  **specification and local mapping module** (`backend/app/foundry_mapping/`, exported to
  `foundry/*.json`) describing ORCA's objects, links, actions, and permissions as Foundry
  concepts — **mapping/spec only, no live Palantir calls or sync**. The mapping preserves
  every ORCA invariant (approved-only reports/graph, need-to-know membership, no raw
  evidence for partner export viewers, audited actions, no CSAM handling). See
  [`docs/v0.9_palantir_foundry_mapping.md`](docs/v0.9_palantir_foundry_mapping.md).
- **v1.0 — AIP-assisted Analyst Copilot, propose-only (current).** A local,
  provider-agnostic AI assistance layer (`backend/app/ai_assist/`) that summarizes approved
  material, proposes candidate entities/relationships, drafts report sections, checks
  citations, and flags review gaps — **always proposed-only, human-reviewed, and audited**.
  Default offline deterministic mock provider (no credentials); designed to map onto
  Palantir AIP later. Partner export viewers cannot access it. See
  [`docs/v1.0_aip_assisted_analyst_copilot.md`](docs/v1.0_aip_assisted_analyst_copilot.md).
- **v1.1 — Foundry Connection Spike.** The smallest safe step from
  *Palantir-ready* toward *Palantir-connected*: a Foundry connection **configuration shape**,
  a **read-only** client abstraction, a deterministic **mock client**, honest real-client
  scaffolding, and a secret-free **health check** (`GET /api/v1/integrations/foundry/health`
  and `python -m app.foundry.health`). Disabled by default; **no credentials needed** for
  dev/CI; **no secrets committed**; not full sync and not live AIP. See
  [`docs/v1.1_foundry_connection_spike.md`](docs/v1.1_foundry_connection_spike.md).
- **v1.2 — Foundry REST Connector.** A real, **read-only** connector
  (`RestFoundryClient`, httpx) behind the v1.1 abstraction: OAuth2 client-credentials **or**
  pre-issued bearer-token auth, calling Foundry's documented **v2 ontology/object endpoints**
  (`GET /api/v2/ontologies` for the health check; object-type/object reads on demand).
  Default client when Foundry is enabled (`ORCA_FOUNDRY_CLIENT=rest`); still disabled by
  default, still read-only, still secret-free in logs/errors. **Verified read-only against the
  live ORCA tenant** (auth + ontology + object-type + object reads via a user token); tests use
  an injected mock transport (no live tenant).
  See [`docs/v1.2_foundry_rest_connector.md`](docs/v1.2_foundry_rest_connector.md).
- **v1.3 — Foundry Read Endpoints.** Admin-only, **read-only**
  endpoints that surface the connector's reads inside the ORCA API
  (`/integrations/foundry/discover`, `/object-types/{t}`, `/objects/{t}`, `/objects/{t}/{id}`),
  with an admin **preview UI** (`/foundry`). Every response carries a `mode` (`mock`/`real`);
  the deterministic mock answers when Foundry is disabled (so dev/CI need no tenant); non-admins
  get generic 403s; connector errors map to secret-free 400/502.
  See [`docs/v1.3_foundry_read_endpoints.md`](docs/v1.3_foundry_read_endpoints.md).
- **v1.4 — Foundry Import (current).** An admin can **import Foundry objects
  into ORCA as entities** (`POST /integrations/foundry/import`, and an import form on the
  `/foundry` page). **Read-only against Foundry** — the only write is to ORCA's deduplicated
  entity store, so re-importing is idempotent. Admin-only; `limit`-bounded; `entity_type`
  validated; imported entities are unverified reference data (assertions that use them still go
  through review). See [`docs/v1.4_foundry_import.md`](docs/v1.4_foundry_import.md).

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

The backend runs against an **in-memory store by default** (no database required) — set
`ORCA_STORAGE_BACKEND=postgres` to use PostgreSQL. See [`backend/README.md`](backend/README.md)
and [`frontend/README.md`](frontend/README.md) for details, and
[`docs/demo_walkthrough.md`](docs/demo_walkthrough.md) for a full guided demo.

## Authentication & demo users (dev)

Auth is dev-only at v1.0: a request acts as the user named in the `X-ORCA-User` header
(the frontend's user switcher sets it via a cookie); the default is `admin`. The in-memory
backend seeds one user per role plus one deliberately unassigned user:

| Username  | Global role             | Seeded case access (demo case) |
| --------- | ----------------------- | ------------------------------ |
| `admin`   | admin                   | all cases (superuser)          |
| `casey`   | case_manager            | case manager                   |
| `ana`     | analyst                 | analyst                        |
| `rae`     | reviewer                | reviewer                       |
| `vic`     | viewer                  | viewer                         |
| `partner` | partner_export_viewer   | approved report packages only  |
| `nomad`   | analyst                 | **unassigned** (gets 403s)     |

```bash
# Act as a given user with curl:
curl -s http://localhost:8000/api/v1/cases -H "X-ORCA-User: ana"
```

For PostgreSQL, seed the users after `alembic upgrade head` with `python -m app.db.seed`.

## Running the tests & checks

```bash
# Backend lint + tests (from backend/)
cd backend
ruff check .
python -m pytest -q                       # in-memory; 191 passing + 1 skipped (PG)

# PostgreSQL integration test (optional; needs a migrated DB)
ORCA_RUN_PG_IT=1 ORCA_POSTGRES_DSN=postgresql+psycopg://orca:orca@localhost:5432/orca \
  python -m pytest tests/backend/test_postgres_integration.py -q

# Export the Foundry ontology mapping to foundry/*.json
python -m app.foundry_mapping.export

# Frontend typecheck + build (from frontend/)
cd ../frontend
npm run typecheck
npm run build
```

## Releases

Each milestone is merged to `main` and tagged. (Annotated tags are created at the merge
commit; create the GitHub release from the tag.)

| Tag                                     | Milestone                              |
| --------------------------------------- | -------------------------------------- |
| `v0.5.0-foundation`                     | v0.1–v0.5 foundation                   |
| `v0.6.0-case-membership`                | Case membership & authorization scoping|
| `v0.7.0-evidence-upload`                | Evidence file upload + storage hardening|
| `v0.8.0-report-package-export`          | Report package export                  |
| `v0.9.0-palantir-foundry-mapping`       | Palantir Foundry ontology mapping      |
| `v1.0.0-aip-assisted-analyst-copilot`   | AIP-assisted Analyst Copilot (propose-only)|
| `v1.0.1-release-hardening-demo-audit`   | Release hardening / demo audit         |

## License

See [`LICENSE`](LICENSE). Use of ORCA is subject to the ethical boundaries described
in the [mission](docs/mission.md).
