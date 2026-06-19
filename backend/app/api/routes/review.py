"""Review-queue endpoints — the most important surface in the product.

Listing is open to any analyst; deciding requires review authority and is audited.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import Pagination, current_principal, pagination
from app.core.security import Principal
from app.models.enums import ReviewStatus
from app.schemas.review import ReviewDecisionRequest, ReviewItemRead
from app.services.review_service import ReviewService

router = APIRouter(prefix="/review", tags=["review"])


def _service() -> ReviewService:
    return ReviewService()


@router.get("", response_model=list[ReviewItemRead], summary="List review-queue items")
def list_review_items(
    page: Pagination = Depends(pagination),
    status_filter: ReviewStatus | None = Query(
        ReviewStatus.PROPOSED,
        alias="status",
        description="Filter by status. Defaults to the pending (proposed) queue.",
    ),
) -> list[ReviewItemRead]:
    return _service().list(limit=page.limit, offset=page.offset, status=status_filter)


@router.get("/{item_id}", response_model=ReviewItemRead, summary="Get a review item")
def get_review_item(item_id: UUID) -> ReviewItemRead:
    return _service().get(item_id)


@router.post(
    "/{item_id}/decision",
    response_model=ReviewItemRead,
    summary="Decide a review item (approve / reject / needs_review)",
)
def decide_review_item(
    item_id: UUID,
    request: ReviewDecisionRequest,
    principal: Principal = Depends(current_principal),
) -> ReviewItemRead:
    return _service().decide(item_id, request.decision, principal, note=request.note)
