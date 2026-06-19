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
