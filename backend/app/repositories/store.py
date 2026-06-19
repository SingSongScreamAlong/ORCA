"""In-memory data store for the skeleton / development backend.

It holds every object type in plain dictionaries and seeds a small, coherent example
of the v0.2 analyst loop: a case containing two *approved* advertisements that share a
phone number, an *approved* ``shared_phone`` relationship citing those observations,
and one *proposed* observation still awaiting review. The seed is the analyst loop in
miniature: intake → review → approval → relationship → timeline → report.

The store is process-wide and intentionally simple. The PostgreSQL-backed unit of work
(``app.repositories.sql``) implements the same repository surface for production.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.models.enums import (
    CaseStatus,
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
from app.schemas.case import CaseRead
from app.schemas.cluster import ClusterRead
from app.schemas.entity import EntityRead
from app.schemas.evidence import EvidenceRead
from app.schemas.handling import Handling
from app.schemas.observation import ObservationRead
from app.schemas.relationship import RelationshipRead
from app.schemas.report import ReportRead
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
        self.cases: dict[UUID, CaseRead] = {}
        self.reports: dict[UUID, ReportRead] = {}
        self.review_items: dict[UUID, ReviewItemRead] = {}
        self.audit: list = []  # AuditEntry objects, append-only
        self._seed()

    def _seed(self) -> None:
        now = datetime.now(UTC)
        observed = now - timedelta(days=2)

        # --- Case -------------------------------------------------------------
        case = CaseRead(
            id=uuid4(),
            title="Shared-phone advertisements",
            status=CaseStatus.ACTIVE,
            owner="Development Analyst",
            summary="Two advertisements appear to be linked by a shared phone number.",
            legal_notes="All material is publicly available open-source information.",
            created_at=now,
            updated_at=now,
        )
        self.cases[case.id] = case

        # --- Source -----------------------------------------------------------
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

        # --- Evidence ---------------------------------------------------------
        ev_a = self._evidence("a", "ad-001.png", observed, source.id, now)
        ev_b = self._evidence("b", "ad-002.png", observed, source.id, now)
        for ev in (ev_a, ev_b):
            self.evidence[ev.id] = ev

        # --- Entities ---------------------------------------------------------
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
        username = EntityRead(
            id=uuid4(), entity_type=EntityType.USERNAME, value="jaye_listings",
            confidence=0.6, created_at=now,
        )
        for ent in (phone, ad_a, ad_b, alias, username):
            self.entities[ent.id] = ent

        lawful = Handling(lawful_basis="publicly available information")

        # --- Approved observations (the completed part of the loop) -----------
        obs_a = ObservationRead(
            id=uuid4(), case_id=case.id, timestamp=observed, source_id=source.id,
            collector="seed-loader",
            notes="Advertisement ad-001 listed phone +1 555 555 0142 with alias 'Jaye'.",
            confidence=0.8, status=ReviewStatus.APPROVED, location=None,
            entity_ids=[ad_a.id, phone.id, alias.id], evidence_ids=[ev_a.id],
            handling=lawful, decided_by="Development Analyst", decided_at=now,
            created_at=now,
        )
        obs_b = ObservationRead(
            id=uuid4(), case_id=case.id, timestamp=observed + timedelta(hours=5),
            source_id=source.id, collector="seed-loader",
            notes="Advertisement ad-002 listed the same phone +1 555 555 0142.",
            confidence=0.8, status=ReviewStatus.APPROVED, location=None,
            entity_ids=[ad_b.id, phone.id], evidence_ids=[ev_b.id],
            handling=lawful, decided_by="Development Analyst", decided_at=now,
            created_at=now,
        )
        # --- A proposed observation still awaiting review ---------------------
        obs_c = ObservationRead(
            id=uuid4(), case_id=case.id, timestamp=observed + timedelta(hours=8),
            source_id=source.id, collector="seed-loader",
            notes="Advertisement ad-002 referenced the username 'jaye_listings'.",
            confidence=0.5, status=ReviewStatus.PROPOSED, location=None,
            entity_ids=[ad_b.id, username.id], evidence_ids=[],
            handling=lawful, decided_by=None, decided_at=None, created_at=now,
        )
        for obs in (obs_a, obs_b, obs_c):
            self.observations[obs.id] = obs

        # --- Approved relationship citing the two approved observations -------
        rel = RelationshipRead(
            id=uuid4(), case_id=case.id, source_entity_id=ad_a.id, target_entity_id=ad_b.id,
            relationship_type=RelationshipType.SHARED_PHONE, confidence=0.66,
            origin=Origin.ANALYST_CREATED, status=ReviewStatus.APPROVED,
            observation_ids=[obs_a.id, obs_b.id], created_at=now, updated_at=now,
        )
        self.relationships[rel.id] = rel

        # --- Candidate cluster ------------------------------------------------
        cluster = ClusterRead(
            id=uuid4(), title="Shared phone +1 555 555 0142", status=ClusterStatus.PROPOSED,
            confidence=0.6, origin=Origin.SYSTEM_PROPOSED,
            entity_ids=[ad_a.id, ad_b.id, phone.id, alias.id],
            observation_ids=[obs_a.id, obs_b.id], created_at=now,
        )
        self.clusters[cluster.id] = cluster

        # --- Review item for the proposed observation -------------------------
        review = ReviewItemRead(
            id=uuid4(), item_type=ReviewItemType.PROPOSED_OBSERVATION,
            subject_type="observation", subject_id=obs_c.id, case_id=case.id,
            rationale=(
                "Observation intake: ad-002 referenced username 'jaye_listings'. "
                "Awaiting analyst review before it can support relationships."
            ),
            confidence=0.5, evidence_ids=[], status=ReviewStatus.PROPOSED,
            decided_by=None, decided_at=None, created_at=now,
        )
        self.review_items[review.id] = review

    @staticmethod
    def _evidence(seed_char: str, name: str, captured, source_id, now) -> EvidenceRead:
        return EvidenceRead(
            id=uuid4(), evidence_type=EvidenceType.SCREENSHOT, sha256=seed_char * 64,
            storage_uri=f"evidence://seed/{name}", content_type="image/png",
            captured_at=captured, source_id=source_id,
            description=f"Screenshot of advertisement {name}.", created_at=now,
        )


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
    store.cases.clear()
    store.reports.clear()
    store.review_items.clear()
    store.audit.clear()
    store._seed()
