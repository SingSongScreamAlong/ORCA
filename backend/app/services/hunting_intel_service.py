"""Hunting Grounds — AOR intelligence (cross-venue link analysis).

The analytical payoff of "locate, don't collect": once identifiers are pulled from leads across
many monitored venues, the question that builds a case is *which ones recur*. A phone, wallet,
``.onion`` service, or handle located from **two or more** venues is a **cross-venue link** — the
strongest signal that separate listings are one operation.

This service is **read-only** and proposes nothing: it gives the operator a common operating
picture of the AOR (and feeds the same cross-venue counts into the LE referral dossier). Pointers
and metadata only; no media.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from app.models.enums import HuntingSourceStatus
from app.repositories.uow import UnitOfWork
from app.schemas.hunting import HuntingIntelPicture, HuntingSourceRead, IntelIdentifier
from app.services.hunting_lead_service import hunting_collector_marker

_MAX = 5000  # recon scale


class HuntingIntelService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def monitored_sources(self, aor: str | None = None) -> list[HuntingSourceRead]:
        return [
            s
            for s in self.uow.hunting_sources.list()
            if s.status == HuntingSourceStatus.MONITORED
            and (aor is None or s.aor.lower() == aor.lower())
        ]

    def entity_source_index(self, sources: list[HuntingSourceRead]) -> dict[UUID, set[UUID]]:
        """Map each located entity id -> the set of source ids whose leads reference it.

        Correlates by the canonical collector marker, filtered at the repository per source.
        """
        index: dict[UUID, set[UUID]] = defaultdict(set)
        for source in sources:
            marker = hunting_collector_marker(source.id)
            for obs in self.uow.observations.list(collector=marker, limit=_MAX):
                for eid in obs.entity_ids:
                    index[eid].add(source.id)
        return index

    def picture(self, aor: str | None = None) -> HuntingIntelPicture:
        sources = self.monitored_sources(aor)
        name_by_id = {s.id: s.name for s in sources}

        # Build the entity → sources index, and count leads per entity.
        source_index: dict[UUID, set[UUID]] = defaultdict(set)
        lead_count: dict[UUID, int] = defaultdict(int)
        total_leads = 0
        for source in sources:
            marker = hunting_collector_marker(source.id)
            observations = self.uow.observations.list(collector=marker, limit=_MAX)
            total_leads += len(observations)
            for obs in observations:
                for eid in obs.entity_ids:
                    source_index[eid].add(source.id)
                    lead_count[eid] += 1

        identifiers: list[IntelIdentifier] = []
        for eid, src_ids in source_index.items():
            entity = self.uow.entities.get(eid)
            if entity is None:
                continue
            identifiers.append(
                IntelIdentifier(
                    entity_type=entity.entity_type,
                    value=entity.value,
                    source_count=len(src_ids),
                    lead_count=lead_count[eid],
                    sources=sorted(name_by_id[sid] for sid in src_ids if sid in name_by_id),
                )
            )

        cross = sorted(
            (i for i in identifiers if i.source_count >= 2),
            key=lambda i: (i.source_count, i.lead_count),
            reverse=True,
        )
        top = sorted(identifiers, key=lambda i: (i.lead_count, i.source_count), reverse=True)

        return HuntingIntelPicture(
            aor=aor,
            monitored_sources=len(sources),
            leads=total_leads,
            identifiers=len(identifiers),
            cross_venue_count=len(cross),
            cross_venue=cross[:25],
            top_identifiers=top[:10],
        )
