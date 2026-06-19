"""In-memory data store for the skeleton / development backend.

It holds every object type in plain dictionaries and seeds a small, coherent example
of the analyst loop with the v0.3 evidence locker: a case with two *approved*
advertisements that share a phone number, each backed by an *approved* evidence item
(screenshot) carrying a verifiable SHA-256, an *approved* ``shared_phone`` relationship,
and one *proposed* observation still awaiting review.

The PostgreSQL-backed unit of work (``app.repositories.sql``) implements the same
repository surface for production.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.core.content_store import memory_content_store, sha256_hex
from app.models.enums import (
    CaseStatus,
    ClusterStatus,
    EntityType,
    EvidenceStatus,
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
from app.schemas.evidence import EvidenceItemRead, LegalFlags
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
        self.evidence: dict[UUID, EvidenceItemRead] = {}
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

        case = CaseRead(
            id=uuid4(), title="Shared-phone advertisements", status=CaseStatus.ACTIVE,
            owner="Development Analyst",
            summary="Two advertisements appear to be linked by a shared phone number.",
            legal_notes="All material is publicly available open-source information.",
            created_at=now, updated_at=now,
        )
        self.cases[case.id] = case

        source = SourceRead(
            id=uuid4(), source_type=SourceType.WEBSITE, name="Example Classifieds",
            identifier="https://example.invalid/listings", reliability=SourceReliability.MEDIUM,
            description="Public classifieds listings site (illustrative seed source).",
            created_at=now,
        )
        self.sources[source.id] = source

        # --- Entities ---------------------------------------------------------
        def ent(entity_type: EntityType, value: str, confidence: float) -> EntityRead:
            return EntityRead(
                id=uuid4(), entity_type=entity_type, value=value, confidence=confidence, created_at=now
            )

        phone = ent(EntityType.PHONE_NUMBER, "+15555550142", 0.95)
        ad_a = ent(EntityType.ADVERTISEMENT, "ad-001", 1.0)
        ad_b = ent(EntityType.ADVERTISEMENT, "ad-002", 1.0)
        alias = ent(EntityType.ALIAS, "Jaye", 0.6)
        username = ent(EntityType.USERNAME, "jaye_listings", 0.6)
        for entity in (phone, ad_a, ad_b, alias, username):
            self.entities[entity.id] = entity

        lawful = Handling(lawful_basis="publicly available information")

        # --- Observations -----------------------------------------------------
        obs_a = ObservationRead(
            id=uuid4(), case_id=case.id, timestamp=observed, source_id=source.id, collector="seed-loader",
            notes="Advertisement ad-001 listed phone +1 555 555 0142 with alias 'Jaye'.",
            confidence=0.8, status=ReviewStatus.APPROVED, location=None,
            entity_ids=[ad_a.id, phone.id, alias.id],
            handling=lawful, decided_by="Development Analyst", decided_at=now, created_at=now,
        )
        obs_b = ObservationRead(
            id=uuid4(), case_id=case.id, timestamp=observed + timedelta(hours=5), source_id=source.id,
            collector="seed-loader", notes="Advertisement ad-002 listed the same phone +1 555 555 0142.",
            confidence=0.8, status=ReviewStatus.APPROVED, location=None, entity_ids=[ad_b.id, phone.id],
            handling=lawful, decided_by="Development Analyst", decided_at=now, created_at=now,
        )
        obs_c = ObservationRead(
            id=uuid4(), case_id=case.id, timestamp=observed + timedelta(hours=8), source_id=source.id,
            collector="seed-loader", notes="Advertisement ad-002 referenced the username 'jaye_listings'.",
            confidence=0.5, status=ReviewStatus.PROPOSED, location=None, entity_ids=[ad_b.id, username.id],
            handling=lawful, decided_by=None, decided_at=None, created_at=now,
        )
        for obs in (obs_a, obs_b, obs_c):
            self.observations[obs.id] = obs

        # --- Evidence items (with verifiable SHA-256) -------------------------
        ev_a = self._evidence(case.id, source.id, obs_a.id, "Screenshot of ad-001",
                              b"ORCA seed evidence: advertisement ad-001 / +15555550142", now)
        ev_b = self._evidence(case.id, source.id, obs_b.id, "Screenshot of ad-002",
                              b"ORCA seed evidence: advertisement ad-002 / +15555550142", now)
        for ev in (ev_a, ev_b):
            self.evidence[ev.id] = ev

        # --- Approved relationship --------------------------------------------
        rel = RelationshipRead(
            id=uuid4(), case_id=case.id, source_entity_id=ad_a.id, target_entity_id=ad_b.id,
            relationship_type=RelationshipType.SHARED_PHONE, confidence=0.66,
            origin=Origin.ANALYST_CREATED, status=ReviewStatus.APPROVED,
            observation_ids=[obs_a.id, obs_b.id], created_at=now, updated_at=now,
        )
        self.relationships[rel.id] = rel

        cluster = ClusterRead(
            id=uuid4(), title="Shared phone +1 555 555 0142", status=ClusterStatus.PROPOSED,
            confidence=0.6, origin=Origin.SYSTEM_PROPOSED, entity_ids=[ad_a.id, ad_b.id, phone.id, alias.id],
            observation_ids=[obs_a.id, obs_b.id], created_at=now,
        )
        self.clusters[cluster.id] = cluster

        review = ReviewItemRead(
            id=uuid4(), item_type=ReviewItemType.PROPOSED_OBSERVATION, subject_type="observation",
            subject_id=obs_c.id, case_id=case.id,
            rationale=(
                "Observation intake: ad-002 referenced username 'jaye_listings'. "
                "Awaiting analyst review before it can support relationships."
            ),
            confidence=0.5, evidence_ids=[], status=ReviewStatus.PROPOSED,
            decided_by=None, decided_at=None, created_at=now,
        )
        self.review_items[review.id] = review

    @staticmethod
    def _evidence(case_id, source_id, observation_id, title, content: bytes, now) -> EvidenceItemRead:
        digest = memory_content_store.put(content)
        assert digest == sha256_hex(content)
        return EvidenceItemRead(
            id=uuid4(), case_id=case_id, source_id=source_id, observation_id=observation_id,
            title=title, description="Seed evidence (illustrative).",
            evidence_type=EvidenceType.SCREENSHOT,
            storage_uri=f"orca-content://{digest}",
            original_filename=f"{title.lower().replace(' ', '_')}.txt",
            mime_type="text/plain", size_bytes=len(content), sha256=digest, captured_at=now,
            captured_by="seed-loader", access_method="analyst_capture",
            legal_flags=LegalFlags(lawful_basis="publicly available information", partner_approved=False),
            handling_notes=None, status=EvidenceStatus.APPROVED, has_bytes=True, created_by="seed-loader",
            created_at=now,
        )


# Process-wide store instance for the in-memory backend.
store = InMemoryStore()


def reset_store() -> None:
    """Re-seed the store in place. Used by tests to start from a known state."""
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
    memory_content_store.clear()
    store._seed()
