# ORCA Backend

FastAPI service for ORCA. It exposes the ontology objects over a JSON API and enforces
the rules that keep evidence traceable: observations reference a source, relationships
may only cite **approved** observations, and nothing reaches `approved` without an
audited analyst decision.

> **v0.2 — Analyst Loop MVP.** Adds cases, the observation review loop (intake →
> queue → approve/reject/needs_more_review), relationships from approved observations,
> the case timeline, case-scoped audit log, draft-report generation, and a
> production PostgreSQL persistence path (SQLAlchemy unit of work + Alembic). See
> [`../docs/v0.2_analyst_loop.md`](../docs/v0.2_analyst_loop.md). The data access layer
> is selected by `ORCA_STORAGE_BACKEND` (`memory` default, `postgres` for the DB path).
>
> **v0.3 — Evidence Locker + Integrity Layer.** Adds the `EvidenceItem` model, a
> content store (`app/core/content_store.py`) that computes/verifies SHA-256, evidence
> create/link/decide/verify endpoints under `/evidence`, the cross-case linking guard,
> a `quarantined` status, chain-of-custody audit events, and report citations of
> approved evidence. See [`../docs/v0.3_evidence_locker.md`](../docs/v0.3_evidence_locker.md).
>
> **v0.4 — Auth/RBAC.** Adds users + case membership, six roles with a capability matrix
> (`app/core/rbac.py`), the `X-ORCA-User` dev auth (`app/core/security.py`), the
> `require(capability)` route guard (`app/api/deps.py`), separation of duties with an
> audited admin override, and report publishing. Authenticate with the `X-ORCA-User`
> header (default user is configurable via `ORCA_DEV_DEFAULT_USER`). For PostgreSQL, seed
> users with `python -m app.db.seed` after `alembic upgrade head`. See
> [`../docs/v0.4_auth_rbac.md`](../docs/v0.4_auth_rbac.md).
>
> **v0.5 — Relationship Graph & Discovery.** Adds `GraphQueryService`
> (`app/services/graph_query_service.py`) over approved relationships — entity
> neighbourhoods, case subgraphs, and shortest paths — behind `/cases/{id}/graph`,
> `/graph/neighbors/{id}`, and `/graph/path`. See
> [`../docs/v0.5_graph_discovery.md`](../docs/v0.5_graph_discovery.md).
>
> **v0.6 — Case Membership & Authorization Scoping.** Adds need-to-know on top of RBAC:
> `case_members` gains a `case_role` and `status`, `app/services/case_access.py`
> centralises the per-case predicates, and case-keyed guards in `app/api/deps.py`
> (`require_case_material_read`, `require_case_audit_access`,
> `require_case_membership_management`, …) plus service-layer checks scope every read,
> mutation, review, export, and listing. The membership roster has an audited
> add/role-change/deactivate lifecycle (`PATCH`/`DELETE /cases/{id}/members/...`), and
> denials are a generic 403 that never reveals a case's existence. See
> [`../docs/v0.6_case_membership.md`](../docs/v0.6_case_membership.md).
>
> **v0.7 — Evidence File Upload + Storage Hardening.** Adds multipart upload
> (`POST /cases/{id}/evidence/upload`) that hashes and content-addresses bytes via the
> existing content store, a safe-by-default policy (`app/core/upload_policy.py`: reject
> blocked extensions, quarantine unknown MIME types, allow-list the rest; size cap in
> config), role/case-scoped raw download (`GET /evidence/{id}/download`), a mandatory
> safety acknowledgement, and audited upload/download/verify. Upload/storage only. See
> [`../docs/v0.7_evidence_file_upload.md`](../docs/v0.7_evidence_file_upload.md).
>
> **v0.8 — Report Package Export.** Adds `ReportPackage` (model + migration) and
> `app/services/report_package_service.py`, which builds an immutable partner-ready export
> from approved material only: a Markdown report + JSON evidence manifest with content
> hashes (`POST /cases/{id}/report/package`), plus listing/metadata/download endpoints
> (`/report-packages/...`, including ZIP). Generation is role-gated; download is scoped to
> case membership (partner-accessible, no raw evidence/graph/audit). See
> [`../docs/v0.8_report_package_export.md`](../docs/v0.8_report_package_export.md).

> **v1.1 — Foundry Connection Spike.** Adds `app/foundry/` (read-only connection
> scaffolding): `FoundryConfig` (env-driven, disabled by default, secrets redacted), a
> `FoundryClient` protocol, a deterministic `MockFoundryClient`, an honest `RealFoundryClient`
> placeholder, and a secret-free health check (`GET /integrations/foundry/health`,
> `python -m app.foundry.health`). No live Palantir calls or credentials are needed for
> dev/CI. See [`../docs/v1.1_foundry_connection_spike.md`](../docs/v1.1_foundry_connection_spike.md)
> and [`../docs/foundry_connection_setup.md`](../docs/foundry_connection_setup.md).

## Layout

```
app/
  main.py            # FastAPI app factory + domain-error handling
  core/              # config, db/graph connections, security, RBAC, audit
  api/               # routing only (routes/ + deps + router aggregation)
  services/          # domain logic and ontology invariants
  repositories/      # data access (in-memory store today; Postgres/Neo4j is the target)
  models/            # SQLAlchemy ORM — canonical relational schema
  schemas/           # Pydantic models — the API contract
  workers/           # background tasks (proposal/extraction) — propose, never confirm
  collection/        # Hunting Grounds interfaces (definitions only)
migrations/          # Alembic migrations
db/                  # canonical SQL DDL + database notes
```

Dependencies point strictly downward: `api → services → repositories → stores`.

## Running locally

The default backend is **in-memory** and seeded with a small example, so no database is
required:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

Then open:

- `http://localhost:8000/docs` — interactive API docs.
- `http://localhost:8000/api/v1/health` — health and active backend.
- `http://localhost:8000/api/v1/review` — the seeded review queue (the proposed
  `shared_phone` relationship awaiting a decision).

## Endpoints (v0.1)

| Method & path                          | Purpose                                   |
| -------------------------------------- | ----------------------------------------- |
| `GET  /health`                         | Liveness and active storage backend.      |
| `GET  /dashboard/summary`              | Dashboard data (new / changed / review).  |
| `GET  /observations`                   | List observations.                        |
| `POST /observations`                   | Record an observation.                    |
| `GET  /observations/{id}`              | Get one observation.                      |
| `GET  /entities`                       | List entities.                            |
| `POST /entities`                       | Create or resolve an entity.              |
| `GET  /entities/{id}`                  | Get one entity.                           |
| `GET  /relationships`                  | List relationships (filter by status).    |
| `POST /relationships`                  | Submit a relationship (routed to review). |
| `GET  /relationships/{id}`             | Get one relationship.                     |
| `GET  /clusters`                       | List clusters.                            |
| `POST /clusters`                       | Create a cluster.                         |
| `GET  /clusters/{id}`                  | Get one cluster.                          |
| `GET  /review`                         | List review-queue items.                  |
| `GET  /review/{id}`                    | Get one review item.                      |
| `POST /review/{id}/decision`           | Approve / reject / needs_review.          |
| `GET  /sources`, `GET /sources/{id}`   | Source read access.                       |
| `GET  /evidence`, `GET /evidence/{id}` | Evidence metadata read access.            |

All paths are under the configured prefix (`/api/v1` by default).

## The proposal → review loop

The seed data includes two advertisements that share a phone number and a
system-**proposed** `shared_phone` relationship. Approve its review item to see the
relationship transition to `confirmed` and an entry written to the audit log:

```bash
# Find the pending item
curl localhost:8000/api/v1/review

# Approve it (use the id from above)
curl -X POST localhost:8000/api/v1/review/<id>/decision \
     -H 'content-type: application/json' \
     -d '{"decision": "approve"}'
```

## Switching to the database backend (Phase 1)

Set `ORCA_STORAGE_BACKEND=postgres` and provide `ORCA_POSTGRES_DSN` / Neo4j settings.
Run migrations with `alembic upgrade head`. Note: DB-backed repositories are
implemented in Phase 1 — see [`../docs/roadmap.md`](../docs/roadmap.md).

## Tests

```bash
pip install -e ".[dev]"
pytest          # runs ../tests/backend
```
