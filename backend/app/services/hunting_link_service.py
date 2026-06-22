"""Hunting Grounds — cross-venue link proposal.

Turns the AOR intelligence into reviewable case links. When two located identifiers co-occur in
**approved** leads from **two or more** monitored venues, that pair is a strong cross-venue signal —
the same actors operating across listings. This service proposes an ``appears_with`` relationship
for each such pair and routes it to the **review queue** (``system_proposed`` / ``proposed``), so an
analyst confirms it with one decision.

The lawful two-stage loop is preserved end to end: *AI proposes the lead → an analyst approves the
observation → the system proposes the cross-venue link → an analyst approves the link.* Nothing is
auto-confirmed, and only **approved** observations are ever cited (an ontology invariant of the
relationship layer). Pointers and metadata only; no media.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from uuid import UUID

from app.core.audit import new_audit_entry
from app.core.security import Principal
from app.models.enums import RelationshipType, ReviewStatus
from app.repositories.uow import UnitOfWork
from app.schemas.hunting import HuntingLinkResult, ProposedLink
from app.services.hunting_intel_service import HuntingIntelService
from app.services.hunting_lead_service import hunting_collector_marker
from app.services.relationship_service import RelationshipService

_MAX = 5000
_MAX_PROPOSALS = 100  # a single pass can't flood the review queue


class HuntingLinkService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def propose_links(
        self, principal: Principal, *, aor: str | None = None, min_venues: int = 2
    ) -> HuntingLinkResult:
        sources = HuntingIntelService(self.uow).monitored_sources(aor)
        name_by_id = {s.id: s.name for s in sources}

        # Collect APPROVED hunting leads per venue (relationships may only cite approved evidence).
        # For each co-occurring entity pair, track the venues and the supporting approved leads.
        pair_sources: dict[frozenset[UUID], set[UUID]] = defaultdict(set)
        pair_obs: dict[frozenset[UUID], set[UUID]] = defaultdict(set)
        for source in sources:
            marker = hunting_collector_marker(source.id)
            approved = self.uow.observations.list(
                collector=marker, status=ReviewStatus.APPROVED, limit=_MAX
            )
            for obs in approved:
                for a, b in combinations(sorted(set(obs.entity_ids), key=str), 2):
                    pair = frozenset((a, b))
                    pair_sources[pair].add(source.id)
                    pair_obs[pair].add(obs.id)

        existing = self._existing_pairs()
        relationships = RelationshipService(self.uow)
        links: list[ProposedLink] = []

        # Cross-venue pairs first (most venues), deterministic order.
        candidates = sorted(
            (p for p, srcs in pair_sources.items() if len(srcs) >= min_venues),
            key=lambda p: (len(pair_sources[p]), len(pair_obs[p])),
            reverse=True,
        )
        for pair in candidates:
            if pair in existing:
                continue  # already linked — don't re-propose
            if len(links) >= _MAX_PROPOSALS:
                break
            a, b = tuple(pair)
            ea, eb = self.uow.entities.get(a), self.uow.entities.get(b)
            if ea is None or eb is None:
                continue
            venues = pair_sources[pair]
            venue_names = sorted(name_by_id[s] for s in venues if s in name_by_id)
            rel = relationships.propose_system(
                source_entity_id=a,
                target_entity_id=b,
                relationship_type=RelationshipType.APPEARS_WITH,
                confidence=min(0.6, 0.3 + 0.1 * len(venues)),
                observation_ids=sorted(pair_obs[pair], key=str),
                rationale=(
                    f"Cross-venue link: {ea.value} appears with {eb.value} in approved leads from "
                    f"{len(venues)} monitored venues ({', '.join(venue_names)})."
                ),
            )
            existing.add(pair)
            links.append(
                ProposedLink(
                    relationship_id=rel.id,
                    source_value=ea.value,
                    target_value=eb.value,
                    relationship_type=rel.relationship_type.value,
                    venue_count=len(venues),
                )
            )

        self._audit(principal, aor, links)
        return HuntingLinkResult(aor=aor, proposed=len(links), links=links)

    def _existing_pairs(self) -> set[frozenset[UUID]]:
        # Exhaustive: page through every relationship so a pre-existing link is never missed (and
        # thus never re-proposed), regardless of how many relationships the store holds.
        pairs: set[frozenset[UUID]] = set()
        offset = 0
        while True:
            batch = self.uow.relationships.list(limit=_MAX, offset=offset)
            if not batch:
                break
            pairs.update(frozenset((r.source_entity_id, r.target_entity_id)) for r in batch)
            if len(batch) < _MAX:
                break
            offset += _MAX
        return pairs

    def _audit(self, principal: Principal, aor: str | None, links: list[ProposedLink]) -> None:
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="hunting.links.proposed",
                target_type="hunting_links",
                target_id=aor or "all",
                case_id=None,
                context={"aor": aor, "proposed": len(links)},
            )
        )
