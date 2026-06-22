"""Foundry → ORCA import service (v1.4).

Reads objects of one Foundry object type (read-only, via the connector) and materialises
them as ORCA **entities** — the deduplicated, non-asserting reference primitive. Entities are
created exactly as ORCA's own entity service creates them (dedup by ``(entity_type, value)``),
so importing is **idempotent**: re-importing the same objects resolves to the existing
entities rather than duplicating them.

This writes only to ORCA's entity store — never to Foundry. Imported entities assert nothing
on their own; any *use* of them in observations or relationships still passes through ORCA's
review queue ("AI/external proposes, analysts decide"). The import is an admin action.
"""

from __future__ import annotations

from typing import Any

from app.core.security import Principal
from app.repositories.uow import UnitOfWork
from app.schemas.entity import EntityCreate
from app.schemas.foundry import FoundryImportRequest, FoundryImportResult
from app.services.entity_service import EntityService

_DEFAULT_CONFIDENCE = 0.5  # imported references are unverified until corroborated in ORCA


def _coerce_confidence(raw: Any) -> float:
    if isinstance(raw, bool):  # bool is an int subclass — exclude it
        return _DEFAULT_CONFIDENCE
    if isinstance(raw, (int, float)) and 0.0 <= float(raw) <= 1.0:
        return float(raw)
    return _DEFAULT_CONFIDENCE


class FoundryImportService:
    def __init__(self, uow: UnitOfWork, client: Any) -> None:
        self.uow = uow
        self.client = client
        self.entities = EntityService(uow)

    def import_entities(
        self, request: FoundryImportRequest, principal: Principal
    ) -> FoundryImportResult:
        objects = self.client.list_demo_objects(request.object_type, limit=request.limit)
        if not isinstance(objects, list):
            objects = []

        created = 0
        skipped = 0
        materialised = []
        for obj in objects:
            if not isinstance(obj, dict):
                skipped += 1
                continue
            raw = obj.get(request.value_property)
            if raw is None or str(raw).strip() == "":
                skipped += 1
                continue
            value = str(raw).strip()
            confidence = _coerce_confidence(obj.get("confidence"))

            existing = self.uow.entities.find_by_value(request.entity_type, value)
            entity = self.entities.create(
                EntityCreate(
                    entity_type=request.entity_type, value=value, confidence=confidence
                ),
                principal,
            )
            if existing is None:
                created += 1
            materialised.append(entity)

        return FoundryImportResult(
            mode=getattr(self.client, "mode", "unknown"),
            object_type=request.object_type,
            entity_type=request.entity_type,
            value_property=request.value_property,
            read=len(objects),
            created=created,
            resolved_existing=len(materialised) - created,
            skipped=skipped,
            entities=materialised,
        )
