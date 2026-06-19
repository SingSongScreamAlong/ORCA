# Database

ORCA uses two stores. PostgreSQL is the system of record; Neo4j is a derived,
queryable projection of the relationship graph. See
[`docs/architecture.md`](../../docs/architecture.md).

## PostgreSQL

- **Canonical DDL:** [`sql/schema.sql`](sql/schema.sql). It mirrors the ORM models in
  `backend/app/models` and the ontology in `ontology/schema`.
- **Migrations:** managed with Alembic in [`backend/migrations`](../migrations). The
  initial migration (`0001_initial`) creates the same objects as `schema.sql`.
- **Local bootstrap:** `infrastructure/postgres/init/01_schema.sql` is a copy of the
  canonical DDL, applied automatically when the local PostgreSQL container first
  starts.

Enum labels use the lowercase ontology values (e.g. `phone_number`). The ORM stores
the same values (see `app/models/types.py::pg_enum`), so the ORM, the DDL, and the
migration agree.

## Neo4j

- **Constraints/indexes:** `infrastructure/neo4j/init/constraints.cypher`.
- Entities become `(:Entity {id, entity_type, value})` nodes; relationships become
  `[:RELATED {id, relationship_type, confidence}]` edges. Writes use `MERGE`, so
  re-running keeps the projection convergent with the record.

## Running migrations

```bash
cd backend
# Requires ORCA_POSTGRES_DSN to point at a reachable database.
alembic upgrade head
```

## A note on the skeleton

The default backend is in-memory (`ORCA_STORAGE_BACKEND=memory`), so neither store is
required to run the API. The schema and migration here are the Phase 1 target;
DB-backed repositories are implemented in Phase 1 (see [`docs/roadmap.md`](../../docs/roadmap.md)).
