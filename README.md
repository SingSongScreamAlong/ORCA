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
| `tests/`          | Structure and contract tests across the repository.                 |

## Documentation

| Document                                             | Purpose                                                |
| ---------------------------------------------------- | ------------------------------------------------------ |
| [Mission](docs/mission.md)                           | Why ORCA exists and the boundaries it will not cross.  |
| [Architecture](docs/architecture.md)                 | System shape, data stores, and request flow.           |
| [Ontology v0.1](docs/ontology_v0.1.md)               | The object model: observations, entities, relationships.|
| [Analyst workflow](docs/analyst_workflow.md)         | How an analyst moves from observation to report.       |
| [Security](docs/security.md)                         | Access control, evidence integrity, audit, encryption. |
| [Roadmap](docs/roadmap.md)                            | Phased delivery, starting from this skeleton.          |

---

## Status

This repository is an **initial skeleton**. It establishes the structure, the data
model, the API surface, and the analyst-facing screens. Collection ("Hunting
Grounds") is defined as an interface only — no collection logic is implemented.

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
