"""Review-queue data access."""

from __future__ import annotations

from uuid import UUID

from app.models.enums import ReviewStatus
from app.repositories.base import newest_first, paginate
from app.repositories.store import store
from app.schemas.review import ReviewItemRead


class ReviewRepository:
    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: ReviewStatus | None = ReviewStatus.PROPOSED,
    ) -> list[ReviewItemRead]:
        """List review items. Defaults to the pending (``proposed``) queue."""
        values = store.review_items.values()
        if status is not None:
            values = [item for item in values if item.status == status]
        return paginate(newest_first(values), limit=limit, offset=offset)

    def pending_count(self) -> int:
        return sum(1 for i in store.review_items.values() if i.status == ReviewStatus.PROPOSED)

    def get(self, item_id: UUID) -> ReviewItemRead | None:
        return store.review_items.get(item_id)

    def add(self, item: ReviewItemRead) -> ReviewItemRead:
        store.review_items[item.id] = item
        return item

    def replace(self, item: ReviewItemRead) -> ReviewItemRead:
        store.review_items[item.id] = item
        return item
