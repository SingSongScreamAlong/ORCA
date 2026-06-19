# ORCA Ontology — machine-readable definitions

This directory holds the machine-readable form of the ORCA ontology. The narrative
reference is [`docs/ontology_v0.1.md`](../docs/ontology_v0.1.md); these files are the
authoritative, structured definition that code is expected to mirror.

## Layout

| File                         | Defines                                           |
| ---------------------------- | ------------------------------------------------- |
| `schema/enums.yaml`          | Shared enumerations (types, statuses, bands).     |
| `schema/observation.yaml`    | The `Observation` object.                         |
| `schema/entity.yaml`         | The `Entity` object.                              |
| `schema/relationship.yaml`   | The `Relationship` object.                        |
| `schema/evidence.yaml`       | The `Evidence` object.                            |
| `schema/source.yaml`         | The `Source` object.                              |
| `schema/cluster.yaml`        | The `Cluster` object.                             |
| `schema/case.yaml`           | The `Case` object.                                |
| `schema/report.yaml`         | The `Report` object.                              |

## Conventions

- **Version** is `0.1`. Changes are additive within a major version; removing or
  renaming a type, or changing a property's meaning, requires a version bump.
- **`id`** is a UUID on every object.
- **`confidence`** is a float in `[0.0, 1.0]`; see `enums.yaml` for the qualitative
  bands.
- **`origin` / `status`** encode "AI proposes, analysts decide". Nothing reaches a
  `confirmed` state without an analyst action recorded in the audit log.
- **Invariants** are listed per object under `invariants:` and are enforced by the
  backend service layer, not merely documented here.

## Relationship to other layers

```
ontology/schema/*.yaml   ──mirrors──▶  backend/app/models/*.py   (relational ORM)
                         ──mirrors──▶  backend/app/schemas/*.py  (API contract)
                         ──mirrors──▶  infrastructure/postgres/init/*.sql
```

When these disagree, the ontology is the intended source of truth and the others are
brought back into line.
