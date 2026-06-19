"""Review service — where "AI proposes, analysts decide" is enforced.

Listing the queue needs no special authority; deciding (approve / reject /
needs_more_review) requires the ``REVIEW_DECIDE`` capability. Every decision is written
to the append-only audit log and transitions the subject (observation or relationship)
to match.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.audit import new_audit_entry
from app.core.rbac import Capability, can
from app.core.security import Principal
from app.models.enums import ReviewStatus
from app.repositories.uow import UnitOfWork
from app.schemas.review import ReviewDecision, ReviewItemRead
from app.services.authz import authorize_decision
from app.services.errors import NotFoundError, PermissionDenied, ValidationError
from app.services.relationship_service import RelationshipService

_DECISION_STATUS: dict[ReviewDecision, ReviewStatus] = {
    ReviewDecision.APPROVE: ReviewStatus.APPROVED,
    ReviewDecision.REJECT: ReviewStatus.REJECTED,
    ReviewDecision.NEEDS_MORE_REVIEW: ReviewStatus.NEEDS_MORE_REVIEW,
}

_DECIDABLE = (ReviewStatus.PROPOSED, ReviewStatus.NEEDS_MORE_REVIEW)


class ReviewService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: ReviewStatus | None = ReviewStatus.PROPOSED,
        case_id: UUID | None = None,
    ) -> list[ReviewItemRead]:
        return self.uow.reviews.list(limit=limit, offset=offset, status=status, case_id=case_id)

    def pending_count(self) -> int:
        return self.uow.reviews.pending_count()

    def get(self, item_id: UUID) -> ReviewItemRead:
        item = self.uow.reviews.get(item_id)
        if item is None:
            raise NotFoundError(f"Review item {item_id} not found")
        return item

    def decide(
        self,
        item_id: UUID,
        decision: ReviewDecision,
        principal: Principal,
        note: str | None = None,
        override: bool = False,
    ) -> ReviewItemRead:
        if not can(principal.role, Capability.REVIEW_DECIDE):
            raise PermissionDenied("Deciding a review item requires review authority")

        item = self.get(item_id)
        if item.status not in _DECIDABLE:
            raise ValidationError(f"Review item {item_id} is already {item.status.value}")

        # Separation of duties: no self-review without an admin override.
        is_override = authorize_decision(principal, item.created_by, override)

        new_status = _DECISION_STATUS[decision]
        now = datetime.now(UTC)
        updated = item.model_copy(
            update={"status": new_status, "decided_by": principal.id, "decided_at": now}
        )
        self.uow.reviews.replace(updated)

        self._apply_to_subject(item, new_status, principal, now)

        # An override is recorded as a distinct audit event.
        action = "review.override" if is_override else f"review.{decision.value}"
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action=action,
                target_type=item.subject_type,
                target_id=item.subject_id,
                case_id=item.case_id,
                context={
                    "review_item_id": str(item.id),
                    "decision": decision.value,
                    "resulting_status": new_status.value,
                    "override": is_override,
                    "proposer": item.created_by,
                    "note": note,
                },
            )
        )
        return updated

    def _apply_to_subject(
        self, item: ReviewItemRead, new_status: ReviewStatus, principal: Principal, now: datetime
    ) -> None:
        if item.subject_type == "observation":
            observation = self.uow.observations.get(item.subject_id)
            if observation is None:
                raise ValidationError(f"Observation {item.subject_id} no longer exists")
            updated = observation.model_copy(
                update={"status": new_status, "decided_by": principal.id, "decided_at": now}
            )
            self.uow.observations.replace(updated)
        elif item.subject_type == "relationship":
            RelationshipService(self.uow).set_status(item.subject_id, new_status)
