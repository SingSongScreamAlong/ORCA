"""Timeline service.

Builds a case timeline from approved observations and relationship changes. Proposed
and rejected observations never appear on the timeline — it is a record of confirmed
analytic state.
"""

from __future__ import annotations

from uuid import UUID

from app.models.enums import ReviewStatus
from app.repositories.uow import UnitOfWork
from app.schemas.timeline import TimelineEvent, TimelineEventKind
from app.services.errors import NotFoundError


class TimelineService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def for_case(self, case_id: UUID) -> list[TimelineEvent]:
        if self.uow.cases.get(case_id) is None:
            raise NotFoundError(f"Case {case_id} not found")

        events: list[TimelineEvent] = []

        for observation in self.uow.observations.for_case(case_id):
            if observation.status is not ReviewStatus.APPROVED:
                continue  # only approved observations reach the timeline
            events.append(
                TimelineEvent(
                    timestamp=observation.decided_at or observation.created_at,
                    kind=TimelineEventKind.OBSERVATION_APPROVED,
                    summary=observation.notes or "Observation approved.",
                    ref_type="observation",
                    ref_id=observation.id,
                )
            )

        for relationship in self.uow.relationships.for_case(case_id):
            if relationship.status is ReviewStatus.REJECTED:
                continue
            approved = relationship.status is ReviewStatus.APPROVED
            events.append(
                TimelineEvent(
                    timestamp=relationship.updated_at if approved else relationship.created_at,
                    kind=(
                        TimelineEventKind.RELATIONSHIP_APPROVED
                        if approved
                        else TimelineEventKind.RELATIONSHIP_CREATED
                    ),
                    summary=(
                        f"{relationship.relationship_type.value} relationship "
                        f"({len(relationship.observation_ids)} supporting observation(s))"
                    ),
                    ref_type="relationship",
                    ref_id=relationship.id,
                )
            )

        # Newest first.
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events
