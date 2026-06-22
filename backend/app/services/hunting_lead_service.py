"""Hunting Grounds → review: lead ingestion (propose-only seam).

A *lead* from a **monitored** Hunting Grounds source becomes a **proposed observation** in
ORCA's review queue — exactly like any other intake. It is never auto-approved: an analyst
decides, citing evidence, before it can support a relationship. This is the bridge that makes
a future collector useful without ever bypassing "the system proposes, analysts decide".

Safety:
* **Monitored-only.** A lead can only be ingested from a source the registry has moved to
  ``monitored`` (which required an administrator's authorization with a lawful basis).
* **CSAM-safe by construction.** A lead carries text and entity hints only — there is no media
  field — so the pipeline cannot pull or store imagery. Leads are flagged for legal review.
* **Lawful basis flows through.** The observation inherits the source's recorded lawful basis.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.security import Principal
from app.models.enums import HuntingSourceStatus, SourceReliability, SourceType
from app.repositories.uow import UnitOfWork
from app.schemas.entity import EntityCreate
from app.schemas.handling import Handling
from app.schemas.hunting import HuntingLeadCreate
from app.schemas.observation import ObservationCreate, ObservationRead
from app.schemas.source import SourceCreate
from app.services.entity_service import EntityService
from app.services.errors import ValidationError
from app.services.hunting_registry_service import HuntingRegistryService
from app.services.observation_service import ObservationService


class HuntingLeadService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def ingest(self, source_id, payload: HuntingLeadCreate, principal: Principal) -> ObservationRead:
        source = HuntingRegistryService(self.uow).get(source_id)  # 404 if missing
        if source.status != HuntingSourceStatus.MONITORED:
            raise ValidationError(
                "Leads can only be ingested from a monitored source "
                f"(this one is '{source.status.value}')."
            )

        # Resolve entity hints into deduplicated ORCA entities.
        entity_ids = []
        for hint in payload.entities:
            entity = EntityService(self.uow).create(
                EntityCreate(entity_type=hint.entity_type, value=hint.value), principal
            )
            entity_ids.append(entity.id)

        observation = ObservationCreate(
            case_id=payload.case_id,
            timestamp=payload.observed_at or datetime.now(UTC),
            source=SourceCreate(
                source_type=SourceType.WEBSITE,
                name=source.name,
                identifier=source.url,
                reliability=SourceReliability.MEDIUM,
                description=f"Hunting Grounds monitored source — {source.aor}.",
            ),
            collector=f"hunting-grounds:{source.name}",
            notes=payload.summary,
            confidence=payload.confidence,
            entity_ids=entity_ids,
            handling=Handling(
                lawful_basis=source.lawful_basis or "Hunting Grounds monitored source",
                requires_legal_review=True,
            ),
        )
        # Enters the review queue as a proposed observation — analysts decide.
        return ObservationService(self.uow).intake(observation, principal)
