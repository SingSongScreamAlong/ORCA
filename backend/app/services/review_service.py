"""Review service — where "AI proposes, analysts decide" is enforced.

Listing the queue requires no special authority; deciding (approve / reject /
needs_review) requires the ``REVIEW_DECIDE`` capability. Every decision is written to
the append-only audit log and, when it confirms or rejects a relationship, the
relationship's status is transitioned to match.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.audit import audit_log
from app.core.rbac import Capability, can
from app.core.security import Principal
from app.models.enums import ReviewStatus
from app.repositories.review_repository import ReviewRepository
from app.schemas.review import ReviewDecision, ReviewItemRead
from app.services.errors import NotFoundError, PermissionDenied, ValidationError
from app.services.relationship_service import RelationshipService

# Map an analyst decision to the resulting review/relationship status.
_DECISION_STATUS: dict[ReviewDecision, ReviewStatus] = {
    ReviewDecision.APPROVE: ReviewStatus.CONFIRMED,
    ReviewDecision.REJECT: ReviewStatus.REJECTED,
    ReviewDecision.NEEDS_REVIEW: ReviewStatus.NEEDS_REVIEW,
}


class ReviewService:
    def __init__(self) -> None:
        self._reviews = ReviewRepository()
        self._relationships = RelationshipService()

    def list(self, *, limit: int = 50, offset: int = 0, status: ReviewStatus | None = None):
        return self._reviews.list(limit=limit, offset=offset, status=status)

    def pending_count(self) -> int:
        return self._reviews.pending_count()

    def get(self, item_id) -> ReviewItemRead:
        item = self._reviews.get(item_id)
        if item is None:
            raise NotFoundError(f"Review item {item_id} not found")
        return item

    def decide(
        self,
        item_id: UUID,
        decision: ReviewDecision,
        principal: Principal,
        note: str | None = None,
    ) -> ReviewItemRead:
        # Separation of duties: only reviewers/admins may decide.
        if not can(principal.role, Capability.REVIEW_DECIDE):
            raise PermissionDenied("Deciding a review item requires review authority")

        item = self.get(item_id)
        if item.status not in (ReviewStatus.PROPOSED, ReviewStatus.NEEDS_REVIEW):
            raise ValidationError(f"Review item {item_id} is already {item.status.value}")

        new_status = _DECISION_STATUS[decision]
        now = datetime.now(UTC)
        updated = item.model_copy(
            update={
                "status": new_status,
                "decided_by": principal.id,
                "decided_at": now,
            }
        )
        self._reviews.replace(updated)

        # Reflect the decision onto the subject (only relationships in this skeleton).
        if item.subject_type == "relationship":
            self._relationships.set_status(item.subject_id, new_status)

        audit_log.record(
            actor_id=principal.id,
            action=f"review.{decision.value}",
            target_type=item.subject_type,
            target_id=item.subject_id,
            context={
                "review_item_id": str(item.id),
                "resulting_status": new_status.value,
                "note": note,
            },
        )
        return updated
