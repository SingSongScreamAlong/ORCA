"""Foundry integration schemas (v1.4 — read-only import to ORCA entities)."""

from __future__ import annotations

from pydantic import Field

from app.models.enums import EntityType
from app.schemas.common import ORCAModel
from app.schemas.entity import EntityRead


class FoundryImportRequest(ORCAModel):
    """Import objects of one Foundry object type as ORCA entities.

    Each read object's ``value_property`` becomes an entity ``value`` under the chosen
    ``entity_type``. Entities are deduplicated by ``(entity_type, value)``, so importing is
    idempotent. Read-only against Foundry — only ORCA's own entity store is written.
    """

    object_type: str = Field(min_length=1, description="Foundry object type API name to read.")
    entity_type: EntityType = Field(description="ORCA entity type to create for each object.")
    value_property: str = Field(
        min_length=1, description="Foundry property whose value becomes the entity value."
    )
    limit: int = Field(10, ge=1, le=50, description="Max objects to read/import (1–50).")


class FoundryImportResult(ORCAModel):
    mode: str  # "mock" | "real" — the data source
    object_type: str
    entity_type: EntityType
    value_property: str
    read: int  # objects read from Foundry
    created: int  # new entities created
    resolved_existing: int  # objects that matched an existing entity (deduped)
    skipped: int  # objects with no usable value_property
    entities: list[EntityRead]
