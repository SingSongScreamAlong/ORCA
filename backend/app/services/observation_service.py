"""Observation service.

Intake records an observation with ``status = proposed`` and routes it to the review
queue. Enforces: an observation references exactly one existing source (or inline
source metadata); referenced entities and evidence must exist; observations are
append-only (status transitions happen via the review service).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.audit import new_audit_entry
from app.core.security import Principal
from app.models.enums import ReviewItemType, ReviewStatus
from app.repositories.uow import UnitOfWork
from app.schemas.observation import ObservationCreate, ObservationRead
from app.schemas.review import ReviewItemRead
from app.schemas.source import SourceRead
from app.services.errors import NotFoundError, ValidationError


class ObservationService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        case_id: UUID | None = None,
        status: ReviewStatus | None = None,
    ) -> list[ObservationRead]:
        return self.uow.observations.list(limit=limit, offset=offset, case_id=case_id, status=status)

    def get(self, observation_id: UUID) -> ObservationRead:
        observation = self.uow.observations.get(observation_id)
        if observation is None:
            raise NotFoundError(f"Observation {observation_id} not found")
        return observation

    def intake(self, payload: ObservationCreate, principal: Principal) -> ObservationRead:
        source_id = self._resolve_source(payload)

        if payload.case_id is not None and self.uow.cases.get(payload.case_id) is None:
            raise ValidationError(f"Case {payload.case_id} does not exist")

        for entity_id in payload.entity_ids:
            if self.uow.entities.get(entity_id) is None:
                raise ValidationError(f"Referenced entity {entity_id} does not exist")

        observation = ObservationRead(
            id=uuid4(),
            case_id=payload.case_id,
            timestamp=payload.timestamp,
            source_id=source_id,
            collector=payload.collector or principal.id,
            location=payload.location,
            notes=payload.notes,
            confidence=payload.confidence,
            status=ReviewStatus.PROPOSED,
            entity_ids=list(payload.entity_ids),
            handling=payload.handling,
            decided_by=None,
            decided_at=None,
            created_at=datetime.now(UTC),
        )
        self.uow.observations.add(observation)
        self._enqueue_review(observation)
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="observation.intake",
                target_type="observation",
                target_id=observation.id,
                case_id=observation.case_id,
                context={"confidence": observation.confidence},
            )
        )
        return observation

    # --- helpers -----------------------------------------------------------------

    def _resolve_source(self, payload: ObservationCreate) -> UUID:
        if payload.source_id is not None:
            if self.uow.sources.get(payload.source_id) is None:
                raise ValidationError(f"Source {payload.source_id} does not exist")
            return payload.source_id

        # Inline source metadata — create the source.
        assert payload.source is not None  # guaranteed by schema validator
        source = SourceRead(
            id=uuid4(),
            source_type=payload.source.source_type,
            name=payload.source.name,
            identifier=payload.source.identifier,
            reliability=payload.source.reliability,
            description=payload.source.description,
            created_at=datetime.now(UTC),
        )
        self.uow.sources.add(source)
        return source.id

    def _enqueue_review(self, observation: ObservationRead) -> ReviewItemRead:
        rationale = (
            "Observation intake awaiting review: "
            f"{observation.notes or 'recorded fact'} "
            f"(collector {observation.collector})."
        )
        item = ReviewItemRead(
            id=uuid4(),
            item_type=ReviewItemType.PROPOSED_OBSERVATION,
            subject_type="observation",
            subject_id=observation.id,
            case_id=observation.case_id,
            rationale=rationale,
            confidence=observation.confidence,
            evidence_ids=[],  # evidence is added to the locker and linked separately (v0.3)
            status=ReviewStatus.PROPOSED,
            decided_by=None,
            decided_at=None,
            created_at=datetime.now(UTC),
        )
        return self.uow.reviews.add(item)
