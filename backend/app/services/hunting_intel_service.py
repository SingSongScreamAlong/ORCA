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

from app.models.enums import EntityType, HuntingSourceStatus
from app.repositories.uow import UnitOfWork
from app.schemas.hunting import (
    CoOccurringIdentifier,
    HuntingIntelPicture,
    HuntingSourceRead,
    IdentifierAppearance,
    IdentifierDossier,
    IntelIdentifier,
    OperationCluster,
    OperationMember,
    ReferralRelationship,
    ReferralSource,
)
from app.services.hunting_lead_service import hunting_collector_marker

_MAX = 5000  # recon scale
_MAX_OPERATION = 250  # cap the connected-component traversal so a huge graph can't run away


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

    def identifier_dossier(
        self, entity_type: EntityType, value: str
    ) -> IdentifierDossier | None:
        """Pivot on one located identifier: every monitored venue it appears in, the text leads,
        the AORs, and the identifiers it co-occurs with. ``None`` if no such identifier was located.

        This is the per-identifier axis that complements the AOR picture (what recurs) and the
        per-source referral (one venue) — the answer to "where is this one phone/handle/wallet?"
        for an analyst assembling an LE referral. Read-only; pointers and metadata only.
        """
        entity = self.uow.entities.find_by_value(entity_type, value)
        if entity is None:
            return None

        appearances: list[IdentifierAppearance] = []
        aors: set[str] = set()
        co_counts: dict[UUID, int] = defaultdict(int)  # co-occurring entity id -> shared leads
        for source in self.monitored_sources():
            marker = hunting_collector_marker(source.id)
            for obs in self.uow.observations.list(collector=marker, limit=_MAX):
                if entity.id not in obs.entity_ids:
                    continue
                appearances.append(
                    IdentifierAppearance(
                        source_id=source.id,
                        source_name=source.name,
                        source_url=source.url,
                        aor=source.aor,
                        observation_id=obs.id,
                        summary=obs.notes or "",
                        observed_at=obs.timestamp,
                        status=obs.status.value,
                    )
                )
                aors.add(source.aor)
                for other in obs.entity_ids:
                    if other != entity.id:
                        co_counts[other] += 1

        appearances.sort(key=lambda a: a.observed_at)
        co_occurring: list[CoOccurringIdentifier] = []
        for oid, shared in sorted(co_counts.items(), key=lambda kv: kv[1], reverse=True):
            other = self.uow.entities.get(oid)
            if other is not None:
                co_occurring.append(
                    CoOccurringIdentifier(
                        entity_type=other.entity_type, value=other.value, shared_leads=shared
                    )
                )

        return IdentifierDossier(
            entity_type=entity.entity_type,
            value=entity.value,
            venue_count=len({a.source_id for a in appearances}),
            lead_count=len(appearances),
            aors=sorted(aors),
            appearances=appearances,
            co_occurring=co_occurring[:25],
        )

    def _all_relationships(self):
        """Yield every relationship, paged — so a large store never silently truncates the graph."""
        offset = 0
        while True:
            batch = self.uow.relationships.list(limit=_MAX, offset=offset)
            if not batch:
                break
            yield from batch
            if len(batch) < _MAX:
                break
            offset += _MAX

    def operation_cluster(
        self, entity_type: EntityType, value: str
    ) -> OperationCluster | None:
        """The operation around a seed identifier — its connected component.

        Two located identifiers are linked when they co-occur in the same text lead, or a
        relationship ties them; the operation is the transitive closure from the seed across those
        edges. Where the AOR rollup is "everything in a region," this is "everything in one network"
        — regardless of AOR. ``None`` if the seed identifier was never located (unknown entity).
        Read-only; pointers and metadata only.
        """
        seed = self.uow.entities.find_by_value(entity_type, value)
        if seed is None:
            return None

        sources = self.monitored_sources()
        source_by_id = {s.id: s for s in sources}

        # Co-occurrence graph among located identifiers; track venues/leads each appears in.
        adjacency: dict[UUID, set[UUID]] = defaultdict(set)
        entity_sources: dict[UUID, set[UUID]] = defaultdict(set)
        entity_obs: dict[UUID, set[UUID]] = defaultdict(set)
        for source in sources:
            marker = hunting_collector_marker(source.id)
            for obs in self.uow.observations.list(collector=marker, limit=_MAX):
                eids = list(obs.entity_ids)
                for eid in eids:
                    entity_sources[eid].add(source.id)
                    entity_obs[eid].add(obs.id)
                for i, a in enumerate(eids):
                    for b in eids[i + 1:]:
                        adjacency[a].add(b)
                        adjacency[b].add(a)

        # Relationship edges, restricted to located identifiers so the operation stays in-scope.
        located = set(entity_sources)
        rels = list(self._all_relationships())
        for rel in rels:
            a, b = rel.source_entity_id, rel.target_entity_id
            if a in located and b in located:
                adjacency[a].add(b)
                adjacency[b].add(a)

        # BFS from the seed across the graph, capped so a huge network can't run away.
        component: set[UUID] = set()
        frontier = [seed.id]
        truncated = False
        while frontier:
            nid = frontier.pop()
            if nid in component:
                continue
            if len(component) >= _MAX_OPERATION:
                truncated = True
                break
            component.add(nid)
            frontier.extend(nb for nb in adjacency.get(nid, ()) if nb not in component)

        # Members, the venues/AORs they touch, and the relationships among them.
        members: list[OperationMember] = []
        venue_ids: set[UUID] = set()
        lead_ids: set[UUID] = set()
        for eid in component:
            entity = self.uow.entities.get(eid)
            if entity is None:
                continue
            srcs = entity_sources.get(eid, set())
            obs_ids = entity_obs.get(eid, set())
            venue_ids |= srcs
            lead_ids |= obs_ids
            members.append(
                OperationMember(
                    entity_type=entity.entity_type,
                    value=entity.value,
                    venue_count=len(srcs),
                    lead_count=len(obs_ids),
                )
            )
        members.sort(key=lambda m: (m.venue_count, m.lead_count), reverse=True)

        venues = [
            ReferralSource.from_source(source_by_id[sid]) for sid in venue_ids if sid in source_by_id
        ]
        venues.sort(key=lambda s: s.name)
        aors = sorted({source_by_id[sid].aor for sid in venue_ids if sid in source_by_id})

        relationships: list[ReferralRelationship] = []
        for rel in rels:
            if rel.source_entity_id in component or rel.target_entity_id in component:
                s = self.uow.entities.get(rel.source_entity_id)
                t = self.uow.entities.get(rel.target_entity_id)
                if s is None or t is None:
                    continue
                relationships.append(
                    ReferralRelationship(
                        relationship_type=rel.relationship_type.value,
                        source_value=s.value,
                        target_value=t.value,
                        confidence=rel.confidence,
                        status=rel.status.value,
                    )
                )

        return OperationCluster(
            seed_type=seed.entity_type,
            seed_value=seed.value,
            identifier_count=len(members),
            venue_count=len(venue_ids),
            lead_count=len(lead_ids),
            aors=aors,
            members=members,
            venues=venues,
            relationships=relationships,
            truncated=truncated,
        )
