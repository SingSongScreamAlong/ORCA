"""Relationship service.

Central invariants:

* A relationship must reference at least one supporting observation.
* Every cited observation must exist and be **approved** — a relationship cannot rest
  on proposed or rejected evidence.
* Endpoints must be two distinct, existing entities.

An analyst-created relationship (from approved observations) is recorded as
``approved`` and audited. A system-proposed relationship is ``proposed`` and routed to
the review queue; it never enters the confirmed graph without an analyst decision.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.audit import new_audit_entry
from app.core.security import Principal
from app.models.enums import Origin, RelationshipType, ReviewItemType, ReviewStatus
from app.repositories.uow import UnitOfWork
from app.schemas.relationship import RelationshipCreate, RelationshipRead
from app.schemas.review import ReviewItemRead
from app.services.errors import NotFoundError, ValidationError


class RelationshipService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        case_id: UUID | None = None,
        status: ReviewStatus | None = None,
    ) -> list[RelationshipRead]:
        return self.uow.relationships.list(limit=limit, offset=offset, case_id=case_id, status=status)

    def get(self, relationship_id: UUID) -> RelationshipRead:
        relationship = self.uow.relationships.get(relationship_id)
        if relationship is None:
            raise NotFoundError(f"Relationship {relationship_id} not found")
        return relationship

    def create(self, payload: RelationshipCreate, principal: Principal) -> RelationshipRead:
        self._validate_endpoints(payload.source_entity_id, payload.target_entity_id)
        case_id = self._require_approved_observations(payload.observation_ids, payload.case_id)

        now = datetime.now(UTC)
        relationship = RelationshipRead(
            id=uuid4(),
            case_id=case_id,
            source_entity_id=payload.source_entity_id,
            target_entity_id=payload.target_entity_id,
            relationship_type=payload.relationship_type,
            confidence=payload.confidence,
            origin=Origin.ANALYST_CREATED,
            status=ReviewStatus.APPROVED,
            observation_ids=list(payload.observation_ids),
            created_at=now,
            updated_at=now,
        )
        self.uow.relationships.add(relationship)
        self._project(relationship)
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="relationship.created",
                target_type="relationship",
                target_id=relationship.id,
                case_id=case_id,
                context={
                    "relationship_type": relationship.relationship_type.value,
                    "observation_ids": [str(o) for o in relationship.observation_ids],
                },
            )
        )
        return relationship

    def propose_system(
        self,
        *,
        source_entity_id: UUID,
        target_entity_id: UUID,
        relationship_type: RelationshipType,
        confidence: float,
        observation_ids: list[UUID],
        rationale: str | None = None,
    ) -> RelationshipRead:
        """Record a system-proposed relationship and route it to the review queue.

        Used by workers. The relationship is ``system_proposed`` / ``proposed`` and only
        becomes ``approved`` through an analyst decision. Cited observations must already
        be approved.
        """
        self._validate_endpoints(source_entity_id, target_entity_id)
        case_id = self._require_approved_observations(observation_ids, None)

        now = datetime.now(UTC)
        relationship = RelationshipRead(
            id=uuid4(),
            case_id=case_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            confidence=confidence,
            origin=Origin.SYSTEM_PROPOSED,
            status=ReviewStatus.PROPOSED,
            observation_ids=list(observation_ids),
            created_at=now,
            updated_at=now,
        )
        self.uow.relationships.add(relationship)
        self._enqueue_review(relationship, rationale)
        self.uow.audit.record(
            new_audit_entry(
                actor_id="system",
                action="relationship.proposed",
                target_type="relationship",
                target_id=relationship.id,
                case_id=case_id,
                context={"relationship_type": relationship.relationship_type.value},
            )
        )
        return relationship

    def set_status(self, relationship_id: UUID, status: ReviewStatus) -> RelationshipRead:
        relationship = self.get(relationship_id)
        updated = relationship.model_copy(update={"status": status, "updated_at": datetime.now(UTC)})
        self.uow.relationships.replace(updated)
        if status is ReviewStatus.APPROVED:
            self._project(updated)
        return updated

    # --- helpers -----------------------------------------------------------------

    def _validate_endpoints(self, source_entity_id: UUID, target_entity_id: UUID) -> None:
        if source_entity_id == target_entity_id:
            raise ValidationError("A relationship must connect two distinct entities")
        for entity_id in (source_entity_id, target_entity_id):
            if self.uow.entities.get(entity_id) is None:
                raise ValidationError(f"Entity {entity_id} does not exist")

    def _require_approved_observations(
        self, observation_ids: list[UUID], case_id: UUID | None
    ) -> UUID | None:
        if not observation_ids:
            raise ValidationError("A relationship must reference at least one observation")
        resolved_case = case_id
        for observation_id in observation_ids:
            observation = self.uow.observations.get(observation_id)
            if observation is None:
                raise ValidationError(f"Supporting observation {observation_id} does not exist")
            if observation.status is not ReviewStatus.APPROVED:
                raise ValidationError(
                    f"Observation {observation_id} is {observation.status.value}; relationships may "
                    "only cite approved observations"
                )
            if resolved_case is None:
                resolved_case = observation.case_id
        return resolved_case

    def _enqueue_review(self, relationship: RelationshipRead, rationale: str | None) -> ReviewItemRead:
        rationale = rationale or (
            f"{relationship.relationship_type.value}: proposed link supported by "
            f"{len(relationship.observation_ids)} approved observation(s)."
        )
        evidence: list[UUID] = []
        for observation_id in relationship.observation_ids:
            for item in self.uow.evidence.for_observation(observation_id):
                evidence.append(item.id)
        item = ReviewItemRead(
            id=uuid4(),
            item_type=ReviewItemType.PROPOSED_RELATIONSHIP,
            subject_type="relationship",
            subject_id=relationship.id,
            case_id=relationship.case_id,
            created_by="system",
            rationale=rationale,
            confidence=relationship.confidence,
            evidence_ids=evidence,
            status=ReviewStatus.PROPOSED,
            decided_by=None,
            decided_at=None,
            created_at=datetime.now(UTC),
        )
        return self.uow.reviews.add(item)

    def _project(self, relationship: RelationshipRead) -> None:
        for entity_id in (relationship.source_entity_id, relationship.target_entity_id):
            entity = self.uow.entities.get(entity_id)
            if entity is not None:
                self.uow.graph.upsert_entity(entity.id, entity.entity_type, entity.value)
        self.uow.graph.upsert_relationship(
            relationship.id,
            relationship.source_entity_id,
            relationship.target_entity_id,
            relationship.relationship_type,
            relationship.confidence,
        )
