"""Illustrative worker: propose ``shared_phone`` relationships.

This embodies "AI proposes, analysts decide". It looks for pairs of entities that both
co-occur with the same ``phone_number`` entity across observations, and proposes a
``shared_phone`` relationship between them — supported by those observations and routed
to the review queue. It confirms nothing.

The logic is deliberately simple and operates on the in-memory store. It is here to
show the shape of a proposal worker, not to be a complete entity-resolution system.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from uuid import UUID

from app.models.enums import EntityType, RelationshipType, ReviewStatus
from app.repositories.store import store
from app.schemas.relationship import RelationshipRead
from app.services.relationship_service import RelationshipService
from app.workers.tasks import task


def _existing_pair_index() -> set[frozenset[UUID]]:
    """Pairs that already have a (non-rejected) shared_phone relationship."""
    index: set[frozenset[UUID]] = set()
    for rel in store.relationships.values():
        is_shared_phone = rel.relationship_type is RelationshipType.SHARED_PHONE
        if is_shared_phone and rel.status is not ReviewStatus.REJECTED:
            index.add(frozenset({rel.source_entity_id, rel.target_entity_id}))
    return index


@task("propose_shared_phone")
def propose_shared_phone_relationships() -> list[RelationshipRead]:
    """Scan observations and propose shared_phone links. Returns what was proposed."""
    service = RelationshipService()
    existing = _existing_pair_index()

    # Map each phone entity -> {non-phone entity -> observations it was seen in}.
    phone_to_parties: dict[UUID, dict[UUID, list[UUID]]] = defaultdict(lambda: defaultdict(list))

    for observation in store.observations.values():
        phone_ids = [
            eid for eid in observation.entity_ids
            if (e := store.entities.get(eid)) and e.entity_type is EntityType.PHONE_NUMBER
        ]
        other_ids = [
            eid for eid in observation.entity_ids
            if (e := store.entities.get(eid)) and e.entity_type is not EntityType.PHONE_NUMBER
        ]
        for phone_id in phone_ids:
            for other_id in other_ids:
                phone_to_parties[phone_id][other_id].append(observation.id)

    proposed: list[RelationshipRead] = []
    for phone_id, parties in phone_to_parties.items():
        phone = store.entities.get(phone_id)
        for a_id, b_id in combinations(sorted(parties, key=str), 2):
            if frozenset({a_id, b_id}) in existing:
                continue
            support = sorted(set(parties[a_id]) | set(parties[b_id]), key=str)
            rationale = (
                f"shared_phone: {phone.value if phone else phone_id} appears in observations "
                f"linking two entities. Supported by {len(support)} observation(s)."
            )
            relationship = service.propose_system(
                source_entity_id=a_id,
                target_entity_id=b_id,
                relationship_type=RelationshipType.SHARED_PHONE,
                confidence=0.6,
                observation_ids=support,
                rationale=rationale,
            )
            proposed.append(relationship)
            existing.add(frozenset({a_id, b_id}))

    return proposed
