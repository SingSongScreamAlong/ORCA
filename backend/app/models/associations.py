"""Association tables for the many-to-many relationships in the ontology.

Keeping these in one place makes the graph of links explicit and keeps the migration
and the ORM in agreement.
"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.models.base import Base


def _fk_col(name: str, table: str) -> Column:
    return Column(
        name,
        PG_UUID(as_uuid=True),
        ForeignKey(f"{table}.id", ondelete="CASCADE"),
        primary_key=True,
    )


def _link(name: str, left: str, left_table: str, right: str, right_table: str) -> Table:
    return Table(
        name,
        Base.metadata,
        _fk_col(left, left_table),
        _fk_col(right, right_table),
    )


# An observation references entities. (Evidence links to an observation via
# EvidenceItem.observation_id — see app/models/evidence.py.)
observation_entities = _link(
    "observation_entities", "observation_id", "observations", "entity_id", "entities"
)

# A relationship is supported by observations.
relationship_observations = _link(
    "relationship_observations",
    "relationship_id", "relationships", "observation_id", "observations",
)

# A cluster contains entities and observations.
cluster_entities = _link(
    "cluster_entities", "cluster_id", "clusters", "entity_id", "entities"
)
cluster_observations = _link(
    "cluster_observations", "cluster_id", "clusters", "observation_id", "observations"
)

# A case is a VIEW over observations, entities, and clusters. The association tables
# carry references only; deleting a case row removes the references, never the
# referenced objects (see ondelete on the case side only).
case_observations = _link(
    "case_observations", "case_id", "cases", "observation_id", "observations"
)
case_entities = _link(
    "case_entities", "case_id", "cases", "entity_id", "entities"
)
case_clusters = _link(
    "case_clusters", "case_id", "cases", "cluster_id", "clusters"
)
