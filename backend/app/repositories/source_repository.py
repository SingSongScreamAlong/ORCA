"""Source and evidence read access."""

from __future__ import annotations

from uuid import UUID

from app.repositories.base import newest_first, paginate
from app.repositories.store import store
from app.schemas.evidence import EvidenceRead
from app.schemas.source import SourceRead


class SourceRepository:
    def list(self, *, limit: int = 50, offset: int = 0) -> list[SourceRead]:
        return paginate(newest_first(store.sources.values()), limit=limit, offset=offset)

    def get(self, source_id: UUID) -> SourceRead | None:
        return store.sources.get(source_id)


class EvidenceRepository:
    def get(self, evidence_id: UUID) -> EvidenceRead | None:
        return store.evidence.get(evidence_id)

    def list(self, *, limit: int = 50, offset: int = 0) -> list[EvidenceRead]:
        return paginate(newest_first(store.evidence.values()), limit=limit, offset=offset)
