"""Review-queue endpoints — the most important surface in the product.

Listing requires read access; deciding requires review authority and is audited.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import Pagination, get_uow, pagination, require
from app.core.rbac import Capability
from app.core.security import Principal
from app.models.enums import ReviewStatus
from app.repositories.uow import UnitOfWork
from app.schemas.review import ReviewDecisionRequest, ReviewItemRead
from app.services.review_service import ReviewService

router = APIRouter(prefix="/review", tags=["review"])


@router.get("", response_model=list[ReviewItemRead], summary="List review-queue items")
def list_review_items(
    page: Pagination = Depends(pagination),
    status_filter: ReviewStatus | None = Query(
        ReviewStatus.PROPOSED,
        alias="status",
        description="Filter by status. Defaults to the pending (proposed) queue.",
    ),
    case_id: UUID | None = Query(None, description="Filter by case."),
    principal: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> list[ReviewItemRead]:
    return ReviewService(uow).list(
        limit=page.limit, offset=page.offset, status=status_filter, case_id=case_id,
        principal=principal,
    )


@router.get("/{item_id}", response_model=ReviewItemRead, summary="Get a review item")
def get_review_item(
    item_id: UUID,
    principal: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> ReviewItemRead:
    return ReviewService(uow).read(item_id, principal)


@router.post(
    "/{item_id}/decision",
    response_model=ReviewItemRead,
    summary="Decide a review item (approve / reject / needs_more_review)",
)
def decide_review_item(
    item_id: UUID,
    request: ReviewDecisionRequest,
    principal: Principal = Depends(require(Capability.REVIEW_DECIDE)),
    uow: UnitOfWork = Depends(get_uow),
) -> ReviewItemRead:
    return ReviewService(uow).decide(
        item_id, request.decision, principal, note=request.note, override=request.override
    )
