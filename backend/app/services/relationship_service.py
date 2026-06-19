"""Relationship service.

Enforces the central invariants:

* A relationship must reference at least one supporting observation.
* Its two endpoints must be distinct, existing entities.
* ``analyst_confirmed`` may only be asserted by a principal with review authority, and
  results in a ``confirmed`` relationship recorded in the audit log.
* Any other relationship submitted through the API is ``proposed`` and is routed to
  the review queue — it never enters the confirmed graph without an analyst decision.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.audit import audit_log
from app.core.rbac import Capability, can
from app.core.security import Principal
from app.models.enums import (
    Origin,
    RelationshipType,
    ReviewItemType,
    ReviewStatus,
)
from app.repositories.entity_repository import EntityRepository
from app.repositories.observation_repository import ObservationRepository
from app.repositories.relationship_repository import RelationshipRepository
from app.repositories.review_repository import ReviewRepository
from app.schemas.relationship import RelationshipCreate, RelationshipRead
from app.schemas.review import ReviewItemRead
from app.services.errors import PermissionDenied, ValidationError
from app.services.graph_sync import get_graph_repository


class RelationshipService:
    def __init__(self) -> None:
        self._relationships = RelationshipRepository()
        self._entities = EntityRepository()
        self._observations = ObservationRepository()
        self._reviews = ReviewRepository()
        self._graph = get_graph_repository()

    def list(self, *, limit: int = 50, offset: int = 0, status: ReviewStatus | None = None):
        return self._relationships.list(limit=limit, offset=offset, status=status)

    def get(self, relationship_id) -> RelationshipRead:
        relationship = self._relationships.get(relationship_id)
        if relationship is None:
            raise ValidationError(f"Relationship {relationship_id} not found")
        return relationship

    def create(self, payload: RelationshipCreate, principal: Principal) -> RelationshipRead:
        if payload.source_entity_id == payload.target_entity_id:
            raise ValidationError("A relationship must connect two distinct entities")

        for entity_id in (payload.source_entity_id, payload.target_entity_id):
            if self._entities.get(entity_id) is None:
                raise ValidationError(f"Entity {entity_id} does not exist")

        # Invariant: at least one supporting observation, and each must exist.
        if not payload.observation_ids:
            raise ValidationError("A relationship must reference at least one observation")
        for observation_id in payload.observation_ids:
            if self._observations.get(observation_id) is None:
                raise ValidationError(f"Supporting observation {observation_id} does not exist")

        now = datetime.now(UTC)

        if payload.relationship_type is RelationshipType.ANALYST_CONFIRMED:
            # A direct analyst assertion. Only a reviewer/admin may do this, and it is
            # recorded as confirmed in the audit log — it is a human decision.
            if not can(principal.role, Capability.REVIEW_DECIDE):
                raise PermissionDenied(
                    "Asserting analyst_confirmed requires review authority"
                )
            relationship = RelationshipRead(
                id=uuid4(),
                source_entity_id=payload.source_entity_id,
                target_entity_id=payload.target_entity_id,
                relationship_type=payload.relationship_type,
                confidence=max(payload.confidence, 0.90),
                origin=Origin.ANALYST_CREATED,
                status=ReviewStatus.CONFIRMED,
                observation_ids=list(payload.observation_ids),
                created_at=now,
                updated_at=now,
            )
            self._relationships.add(relationship)
            self._project(relationship)
            audit_log.record(
                actor_id=principal.id,
                action="relationship.created_confirmed",
                target_type="relationship",
                target_id=relationship.id,
                context={"relationship_type": relationship.relationship_type.value},
            )
            return relationship

        # Any other type goes to the review queue as a proposal.
        relationship = RelationshipRead(
            id=uuid4(),
            source_entity_id=payload.source_entity_id,
            target_entity_id=payload.target_entity_id,
            relationship_type=payload.relationship_type,
            confidence=payload.confidence,
            origin=Origin.ANALYST_CREATED,
            status=ReviewStatus.PROPOSED,
            observation_ids=list(payload.observation_ids),
            created_at=now,
            updated_at=now,
        )
        self._relationships.add(relationship)
        self._enqueue_review(relationship)
        audit_log.record(
            actor_id=principal.id,
            action="relationship.proposed",
            target_type="relationship",
            target_id=relationship.id,
            context={"relationship_type": relationship.relationship_type.value},
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

        Used by workers (see ``app.workers``). The relationship is created with
        ``origin = system_proposed`` and ``status = proposed`` — it never enters the
        confirmed graph without an analyst decision. The proposal is attributed to the
        ``system`` actor in the audit log.
        """
        if source_entity_id == target_entity_id:
            raise ValidationError("A relationship must connect two distinct entities")
        if not observation_ids:
            raise ValidationError("A proposed relationship must reference an observation")

        now = datetime.now(UTC)
        relationship = RelationshipRead(
            id=uuid4(),
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
        self._relationships.add(relationship)
        self._enqueue_review(relationship, rationale=rationale)
        audit_log.record(
            actor_id="system",
            action="relationship.proposed",
            target_type="relationship",
            target_id=relationship.id,
            context={
                "relationship_type": relationship.relationship_type.value,
                "origin": Origin.SYSTEM_PROPOSED.value,
            },
        )
        return relationship

    def set_status(self, relationship_id: UUID, status: ReviewStatus) -> RelationshipRead:
        """Transition a relationship's status (used by the review service)."""
        relationship = self.get(relationship_id)
        updated = relationship.model_copy(
            update={"status": status, "updated_at": datetime.now(UTC)}
        )
        self._relationships.replace(updated)
        if status is ReviewStatus.CONFIRMED:
            self._project(updated)
        return updated

    # --- helpers -----------------------------------------------------------------

    def _evidence_for(self, observation_ids: list[UUID]) -> list[UUID]:
        evidence: list[UUID] = []
        for observation_id in observation_ids:
            observation = self._observations.get(observation_id)
            if observation is not None:
                evidence.extend(observation.evidence_ids)
        return evidence

    def _enqueue_review(
        self, relationship: RelationshipRead, rationale: str | None = None
    ) -> ReviewItemRead:
        rationale = rationale or (
            f"{relationship.relationship_type.value}: proposed link between two entities, "
            f"supported by {len(relationship.observation_ids)} observation(s)."
        )
        item = ReviewItemRead(
            id=uuid4(),
            item_type=ReviewItemType.PROPOSED_RELATIONSHIP,
            subject_type="relationship",
            subject_id=relationship.id,
            rationale=rationale,
            confidence=relationship.confidence,
            evidence_ids=self._evidence_for(relationship.observation_ids),
            status=ReviewStatus.PROPOSED,
            decided_by=None,
            decided_at=None,
            created_at=datetime.now(UTC),
        )
        return self._reviews.add(item)

    def _project(self, relationship: RelationshipRead) -> None:
        """Mirror endpoints and the confirmed edge into the graph projection."""
        for entity_id in (relationship.source_entity_id, relationship.target_entity_id):
            entity = self._entities.get(entity_id)
            if entity is not None:
                self._graph.upsert_entity(entity.id, entity.entity_type, entity.value)
        self._graph.upsert_relationship(
            relationship.id,
            relationship.source_entity_id,
            relationship.target_entity_id,
            relationship.relationship_type,
            relationship.confidence,
        )
