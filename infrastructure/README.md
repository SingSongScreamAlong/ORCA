# Infrastructure

Local orchestration for ORCA: PostgreSQL (system of record) and Neo4j (relationship
graph projection), plus optional backend and frontend containers.

The default backend storage is **in-memory**, so the data stores are not required to
run the API. They are here for Phase 1 onward and for working against the real schema.

## Quick start

```bash
cp env/.env.example .env

# Just the data stores:
docker compose up -d postgres neo4j

# Everything (backend + frontend too):
docker compose --profile app up -d
```

## What starts

| Service    | Port (default) | Notes                                                      |
| ---------- | -------------- | ---------------------------------------------------------- |
| `postgres` | 5432           | Applies `postgres/init/01_schema.sql` on first start.      |
| `neo4j`    | 7474 / 7687    | HTTP browser and Bolt. Constraints applied manually below. |
| `backend`  | 8000           | FastAPI. Only with `--profile app`.                        |
| `frontend` | 3000           | Next.js. Only with `--profile app`.                        |

## PostgreSQL schema

On first start, PostgreSQL runs everything in `postgres/init/`. `01_schema.sql` is a
copy of the canonical DDL in [`backend/db/sql/schema.sql`](../backend/db/sql/schema.sql).
For an existing database, use Alembic instead:

```bash
cd ../backend && alembic upgrade head
```

## Neo4j constraints

The official Neo4j image does not auto-run init scripts. Apply the constraints once the
container is healthy:

```bash
docker compose exec neo4j cypher-shell -u neo4j -p <password> \
  -f /var/lib/neo4j/import/init/constraints.cypher
```

(Source: [`neo4j/init/constraints.cypher`](neo4j/init/constraints.cypher).)

## Notes

- `.env` is git-ignored. `env/.env.example` contains placeholders only — change
  `NEO4J_AUTH` and database credentials before any non-local use.
- Production topology (encryption at rest, secret management, backups) is out of scope
  for the skeleton; see [`docs/security.md`](../docs/security.md) and
  [`docs/roadmap.md`](../docs/roadmap.md).
