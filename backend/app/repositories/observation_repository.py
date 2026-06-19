"""Observation data access."""

from __future__ import annotations

from uuid import UUID

from app.repositories.base import newest_first, paginate
from app.repositories.store import store
from app.schemas.observation import ObservationRead


class ObservationRepository:
    def list(self, *, limit: int = 50, offset: int = 0) -> list[ObservationRead]:
        return paginate(newest_first(store.observations.values()), limit=limit, offset=offset)

    def count(self) -> int:
        return len(store.observations)

    def get(self, observation_id: UUID) -> ObservationRead | None:
        return store.observations.get(observation_id)

    def add(self, observation: ObservationRead) -> ObservationRead:
        # Observations are append-only; we only ever add, never update.
        store.observations[observation.id] = observation
        return observation
