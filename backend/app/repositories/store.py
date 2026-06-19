"""In-memory data store for the skeleton backend.

This holds every object type in plain dictionaries and seeds a small, coherent
example: two advertisements that share a phone number, the observations that record
them, a system-PROPOSED ``shared_phone`` relationship, a candidate cluster, and the
review-queue item that surfaces the relationship for analyst decision. The seed is the
"AI proposes, analysts decide" loop in miniature.

The store is process-wide and intentionally simple. Swapping it for the
PostgreSQL/Neo4j repositories is Phase 1 work and does not change the service or API
layers above it.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.models.enums import (
    ClusterStatus,
    EntityType,
    EvidenceType,
    Origin,
    RelationshipType,
    ReviewItemType,
    ReviewStatus,
    SourceReliability,
    SourceType,
)
from app.schemas.cluster import ClusterRead
from app.schemas.entity import EntityRead
from app.schemas.evidence import EvidenceRead
from app.schemas.observation import ObservationRead
from app.schemas.relationship import RelationshipRead
from app.schemas.review import ReviewItemRead
from app.schemas.source import SourceRead


class InMemoryStore:
    """Process-wide in-memory store keyed by UUID."""

    def __init__(self) -> None:
        self.sources: dict[UUID, SourceRead] = {}
        self.evidence: dict[UUID, EvidenceRead] = {}
        self.entities: dict[UUID, EntityRead] = {}
        self.observations: dict[UUID, ObservationRead] = {}
        self.relationships: dict[UUID, RelationshipRead] = {}
        self.clusters: dict[UUID, ClusterRead] = {}
        self.review_items: dict[UUID, ReviewItemRead] = {}
        self._seed()

    def _seed(self) -> None:
        now = datetime.now(UTC)
        observed = now - timedelta(days=2)

        # --- Source -------------------------------------------------------------
        source = SourceRead(
            id=uuid4(),
            source_type=SourceType.WEBSITE,
            name="Example Classifieds",
            identifier="https://example.invalid/listings",
            reliability=SourceReliability.MEDIUM,
            description="Public classifieds listings site (illustrative seed source).",
            created_at=now,
        )
        self.sources[source.id] = source

        # --- Evidence (immutable artifacts) ------------------------------------
        ev_a = EvidenceRead(
            id=uuid4(),
            evidence_type=EvidenceType.SCREENSHOT,
            sha256="a" * 64,
            storage_uri="evidence://seed/ad-001.png",
            content_type="image/png",
            captured_at=observed,
            source_id=source.id,
            description="Screenshot of advertisement ad-001.",
            created_at=now,
        )
        ev_b = EvidenceRead(
            id=uuid4(),
            evidence_type=EvidenceType.SCREENSHOT,
            sha256="b" * 64,
            storage_uri="evidence://seed/ad-002.png",
            content_type="image/png",
            captured_at=observed,
            source_id=source.id,
            description="Screenshot of advertisement ad-002.",
            created_at=now,
        )
        for ev in (ev_a, ev_b):
            self.evidence[ev.id] = ev

        # --- Entities (deduplicated by type + value) ---------------------------
        phone = EntityRead(
            id=uuid4(), entity_type=EntityType.PHONE_NUMBER, value="+15555550142",
            confidence=0.95, created_at=now,
        )
        ad_a = EntityRead(
            id=uuid4(), entity_type=EntityType.ADVERTISEMENT, value="ad-001",
            confidence=1.0, created_at=now,
        )
        ad_b = EntityRead(
            id=uuid4(), entity_type=EntityType.ADVERTISEMENT, value="ad-002",
            confidence=1.0, created_at=now,
        )
        alias = EntityRead(
            id=uuid4(), entity_type=EntityType.ALIAS, value="Jaye",
            confidence=0.6, created_at=now,
        )
        for ent in (phone, ad_a, ad_b, alias):
            self.entities[ent.id] = ent

        # --- Observations (the atomic units of truth) --------------------------
        obs_a = ObservationRead(
            id=uuid4(),
            timestamp=observed,
            source_id=source.id,
            collector="seed-loader",
            location=None,
            notes="Advertisement ad-001 listed phone +1 555 555 0142 with alias 'Jaye'.",
            confidence=0.8,
            entity_ids=[ad_a.id, phone.id, alias.id],
            evidence_ids=[ev_a.id],
            created_at=now,
        )
        obs_b = ObservationRead(
            id=uuid4(),
            timestamp=observed + timedelta(hours=5),
            source_id=source.id,
            collector="seed-loader",
            location=None,
            notes="Advertisement ad-002 listed the same phone +1 555 555 0142.",
            confidence=0.8,
            entity_ids=[ad_b.id, phone.id],
            evidence_ids=[ev_b.id],
            created_at=now,
        )
        for obs in (obs_a, obs_b):
            self.observations[obs.id] = obs

        # --- System-proposed relationship (status = proposed) ------------------
        rel = RelationshipRead(
            id=uuid4(),
            source_entity_id=ad_a.id,
            target_entity_id=ad_b.id,
            relationship_type=RelationshipType.SHARED_PHONE,
            confidence=0.66,
            origin=Origin.SYSTEM_PROPOSED,
            status=ReviewStatus.PROPOSED,
            observation_ids=[obs_a.id, obs_b.id],
            created_at=now,
            updated_at=now,
        )
        self.relationships[rel.id] = rel

        # --- Candidate cluster --------------------------------------------------
        cluster = ClusterRead(
            id=uuid4(),
            title="Shared phone +1 555 555 0142",
            status=ClusterStatus.PROPOSED,
            confidence=0.6,
            origin=Origin.SYSTEM_PROPOSED,
            entity_ids=[ad_a.id, ad_b.id, phone.id, alias.id],
            observation_ids=[obs_a.id, obs_b.id],
            created_at=now,
        )
        self.clusters[cluster.id] = cluster

        # --- Review-queue item surfacing the relationship ----------------------
        review = ReviewItemRead(
            id=uuid4(),
            item_type=ReviewItemType.PROPOSED_RELATIONSHIP,
            subject_type="relationship",
            subject_id=rel.id,
            rationale=(
                "shared_phone: +1 555 555 0142 appears in observations for ad-001 and "
                "ad-002. The two advertisements are linked by a shared phone number."
            ),
            confidence=0.66,
            evidence_ids=[ev_a.id, ev_b.id],
            status=ReviewStatus.PROPOSED,
            decided_by=None,
            decided_at=None,
            created_at=now,
        )
        self.review_items[review.id] = review


# Process-wide store instance for the in-memory backend.
store = InMemoryStore()


def reset_store() -> None:
    """Re-seed the store in place. Used by tests to start from a known state.

    Mutates the existing ``store`` object rather than rebinding the global, so modules
    that imported ``store`` by reference continue to see the reset state.
    """
    store.sources.clear()
    store.evidence.clear()
    store.entities.clear()
    store.observations.clear()
    store.relationships.clear()
    store.clusters.clear()
    store.review_items.clear()
    store._seed()
