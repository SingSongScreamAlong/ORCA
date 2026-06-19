"""PostgreSQL-backed repositories and unit of work.

These implement the same surface as the in-memory repositories, over SQLAlchemy ORM
models, converting between ORM rows and Pydantic read models. PostgreSQL is the system
of record. Selected when ``ORCA_STORAGE_BACKEND=postgres``.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import AuditEntry
from app.core.config import get_settings
from app.core.database import new_session
from app.models import (
    AuditLogEntry,
    Case,
    Cluster,
    Entity,
    Evidence,
    Observation,
    Relationship,
    Report,
    ReviewItem,
    Source,
)
from app.models.enums import EntityType, ReviewStatus
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

# --- mappers (ORM -> read model) -------------------------------------------------


def _source(o: Source) -> SourceRead:
    return SourceRead.model_validate(o)


def _evidence(o: Evidence) -> EvidenceRead:
    return EvidenceRead.model_validate(o)


def _entity(o: Entity) -> EntityRead:
    return EntityRead.model_validate(o)


def _case(o: Case) -> CaseRead:
    return CaseRead.model_validate(o)


def _report(o: Report) -> ReportRead:
    return ReportRead.model_validate(o)


def _review(o: ReviewItem) -> ReviewItemRead:
    return ReviewItemRead.model_validate(o)


def _observation(o: Observation) -> ObservationRead:
    return ObservationRead(
        id=o.id,
        case_id=o.case_id,
        timestamp=o.timestamp,
        source_id=o.source_id,
        collector=o.collector,
        location=o.location,
        notes=o.notes,
        confidence=o.confidence,
        status=o.status,
        entity_ids=[e.id for e in o.entities],
        evidence_ids=[ev.id for ev in o.evidence],
        handling=Handling(**(o.handling or {})),
        decided_by=o.decided_by,
        decided_at=o.decided_at,
        created_at=o.created_at,
    )


def _relationship(o: Relationship) -> RelationshipRead:
    return RelationshipRead(
        id=o.id,
        case_id=o.case_id,
        source_entity_id=o.source_entity_id,
        target_entity_id=o.target_entity_id,
        relationship_type=o.relationship_type,
        confidence=o.confidence,
        origin=o.origin,
        status=o.status,
        observation_ids=[obs.id for obs in o.supporting_observations],
        created_at=o.created_at,
        updated_at=o.updated_at,
    )


def _cluster(o: Cluster) -> ClusterRead:
    return ClusterRead(
        id=o.id,
        title=o.title,
        status=o.status,
        confidence=o.confidence,
        origin=o.origin,
        entity_ids=[e.id for e in o.entities],
        observation_ids=[obs.id for obs in o.observations],
        created_at=o.created_at,
    )


def _audit(o: AuditLogEntry) -> AuditEntry:
    return AuditEntry(
        id=o.id,
        actor_id=o.actor_id,
        action=o.action,
        target_type=o.target_type,
        target_id=o.target_id,
        case_id=o.case_id,
        context=o.context,
        created_at=o.created_at,
    )


# --- repositories ----------------------------------------------------------------


class _Repo:
    def __init__(self, session: Session) -> None:
        self.s = session


class SqlSourceRepository(_Repo):
    def get(self, source_id: UUID) -> SourceRead | None:
        o = self.s.get(Source, source_id)
        return _source(o) if o else None

    def list(self, *, limit: int = 50, offset: int = 0) -> list[SourceRead]:
        rows = self.s.scalars(
            select(Source).order_by(Source.created_at.desc()).limit(limit).offset(offset)
        ).all()
        return [_source(o) for o in rows]

    def add(self, read: SourceRead) -> SourceRead:
        o = Source(
            id=read.id, source_type=read.source_type, name=read.name,
            identifier=read.identifier, reliability=read.reliability, description=read.description,
        )
        self.s.add(o)
        self.s.flush()
        return _source(o)


class SqlEvidenceRepository(_Repo):
    def get(self, evidence_id: UUID) -> EvidenceRead | None:
        o = self.s.get(Evidence, evidence_id)
        return _evidence(o) if o else None

    def list(self, *, limit: int = 50, offset: int = 0) -> list[EvidenceRead]:
        rows = self.s.scalars(
            select(Evidence).order_by(Evidence.created_at.desc()).limit(limit).offset(offset)
        ).all()
        return [_evidence(o) for o in rows]

    def add(self, read: EvidenceRead) -> EvidenceRead:
        o = Evidence(
            id=read.id, evidence_type=read.evidence_type, sha256=read.sha256,
            storage_uri=read.storage_uri, content_type=read.content_type,
            captured_at=read.captured_at, source_id=read.source_id, description=read.description,
        )
        self.s.add(o)
        self.s.flush()
        return _evidence(o)


class SqlEntityRepository(_Repo):
    def get(self, entity_id: UUID) -> EntityRead | None:
        o = self.s.get(Entity, entity_id)
        return _entity(o) if o else None

    def list(self, *, limit: int = 50, offset: int = 0) -> list[EntityRead]:
        rows = self.s.scalars(
            select(Entity).order_by(Entity.created_at.desc()).limit(limit).offset(offset)
        ).all()
        return [_entity(o) for o in rows]

    def find_by_value(self, entity_type: EntityType, value: str) -> EntityRead | None:
        o = self.s.scalars(
            select(Entity).where(Entity.entity_type == entity_type, Entity.value == value)
        ).first()
        return _entity(o) if o else None

    def add(self, read: EntityRead) -> EntityRead:
        o = Entity(id=read.id, entity_type=read.entity_type, value=read.value, confidence=read.confidence)
        self.s.add(o)
        self.s.flush()
        return _entity(o)


class SqlObservationRepository(_Repo):
    def get(self, observation_id: UUID) -> ObservationRead | None:
        o = self.s.get(Observation, observation_id)
        return _observation(o) if o else None

    def list(self, *, limit=50, offset=0, case_id=None, status=None) -> list[ObservationRead]:
        stmt = select(Observation)
        if case_id is not None:
            stmt = stmt.where(Observation.case_id == case_id)
        if status is not None:
            stmt = stmt.where(Observation.status == status)
        stmt = stmt.order_by(Observation.created_at.desc()).limit(limit).offset(offset)
        return [_observation(o) for o in self.s.scalars(stmt).all()]

    def for_case(self, case_id: UUID) -> list[ObservationRead]:
        rows = self.s.scalars(select(Observation).where(Observation.case_id == case_id)).all()
        return [_observation(o) for o in rows]

    def add(self, read: ObservationRead) -> ObservationRead:
        o = Observation(
            id=read.id, case_id=read.case_id, timestamp=read.timestamp, source_id=read.source_id,
            collector=read.collector, location=read.location, notes=read.notes,
            confidence=read.confidence, status=read.status, decided_by=read.decided_by,
            decided_at=read.decided_at, handling=read.handling.model_dump(),
        )
        if read.entity_ids:
            o.entities = list(self.s.scalars(select(Entity).where(Entity.id.in_(read.entity_ids))).all())
        if read.evidence_ids:
            o.evidence = list(
                self.s.scalars(select(Evidence).where(Evidence.id.in_(read.evidence_ids))).all()
            )
        self.s.add(o)
        self.s.flush()
        return _observation(o)

    def replace(self, read: ObservationRead) -> ObservationRead:
        o = self.s.get(Observation, read.id)
        o.status = read.status
        o.decided_by = read.decided_by
        o.decided_at = read.decided_at
        o.confidence = read.confidence
        o.notes = read.notes
        o.handling = read.handling.model_dump()
        self.s.flush()
        return _observation(o)


class SqlRelationshipRepository(_Repo):
    def get(self, relationship_id: UUID) -> RelationshipRead | None:
        o = self.s.get(Relationship, relationship_id)
        return _relationship(o) if o else None

    def list(self, *, limit=50, offset=0, case_id=None, status=None) -> list[RelationshipRead]:
        stmt = select(Relationship)
        if case_id is not None:
            stmt = stmt.where(Relationship.case_id == case_id)
        if status is not None:
            stmt = stmt.where(Relationship.status == status)
        stmt = stmt.order_by(Relationship.created_at.desc()).limit(limit).offset(offset)
        return [_relationship(o) for o in self.s.scalars(stmt).all()]

    def for_case(self, case_id: UUID) -> list[RelationshipRead]:
        rows = self.s.scalars(select(Relationship).where(Relationship.case_id == case_id)).all()
        return [_relationship(o) for o in rows]

    def add(self, read: RelationshipRead) -> RelationshipRead:
        o = Relationship(
            id=read.id, case_id=read.case_id, source_entity_id=read.source_entity_id,
            target_entity_id=read.target_entity_id, relationship_type=read.relationship_type,
            confidence=read.confidence, origin=read.origin, status=read.status,
        )
        if read.observation_ids:
            o.supporting_observations = list(
                self.s.scalars(select(Observation).where(Observation.id.in_(read.observation_ids))).all()
            )
        self.s.add(o)
        self.s.flush()
        return _relationship(o)

    def replace(self, read: RelationshipRead) -> RelationshipRead:
        o = self.s.get(Relationship, read.id)
        o.status = read.status
        o.confidence = read.confidence
        self.s.flush()
        return _relationship(o)


class SqlClusterRepository(_Repo):
    def get(self, cluster_id: UUID) -> ClusterRead | None:
        o = self.s.get(Cluster, cluster_id)
        return _cluster(o) if o else None

    def list(self, *, limit: int = 50, offset: int = 0) -> list[ClusterRead]:
        rows = self.s.scalars(
            select(Cluster).order_by(Cluster.created_at.desc()).limit(limit).offset(offset)
        ).all()
        return [_cluster(o) for o in rows]

    def add(self, read: ClusterRead) -> ClusterRead:
        o = Cluster(
            id=read.id, title=read.title, status=read.status,
            confidence=read.confidence, origin=read.origin,
        )
        if read.entity_ids:
            o.entities = list(self.s.scalars(select(Entity).where(Entity.id.in_(read.entity_ids))).all())
        if read.observation_ids:
            o.observations = list(
                self.s.scalars(select(Observation).where(Observation.id.in_(read.observation_ids))).all()
            )
        self.s.add(o)
        self.s.flush()
        return _cluster(o)


class SqlCaseRepository(_Repo):
    def get(self, case_id: UUID) -> CaseRead | None:
        o = self.s.get(Case, case_id)
        return _case(o) if o else None

    def list(self, *, limit: int = 50, offset: int = 0) -> list[CaseRead]:
        rows = self.s.scalars(
            select(Case).order_by(Case.created_at.desc()).limit(limit).offset(offset)
        ).all()
        return [_case(o) for o in rows]

    def add(self, read: CaseRead) -> CaseRead:
        o = Case(
            id=read.id, title=read.title, status=read.status, owner=read.owner,
            summary=read.summary, legal_notes=read.legal_notes,
        )
        self.s.add(o)
        self.s.flush()
        return _case(o)

    def replace(self, read: CaseRead) -> CaseRead:
        o = self.s.get(Case, read.id)
        o.title = read.title
        o.status = read.status
        o.summary = read.summary
        o.legal_notes = read.legal_notes
        self.s.flush()
        return _case(o)


class SqlReportRepository(_Repo):
    def get(self, report_id: UUID) -> ReportRead | None:
        o = self.s.get(Report, report_id)
        return _report(o) if o else None

    def list(self, *, case_id: UUID | None = None) -> list[ReportRead]:
        stmt = select(Report)
        if case_id is not None:
            stmt = stmt.where(Report.case_id == case_id)
        rows = self.s.scalars(stmt.order_by(Report.created_at.desc())).all()
        return [_report(o) for o in rows]

    def add(self, read: ReportRead) -> ReportRead:
        o = Report(
            id=read.id, case_id=read.case_id, title=read.title, author=read.author,
            status=read.status, body=read.body,
        )
        self.s.add(o)
        self.s.flush()
        return _report(o)


class SqlReviewRepository(_Repo):
    def get(self, item_id: UUID) -> ReviewItemRead | None:
        o = self.s.get(ReviewItem, item_id)
        return _review(o) if o else None

    def list(self, *, limit=50, offset=0, status=ReviewStatus.PROPOSED, case_id=None) -> list[ReviewItemRead]:
        stmt = select(ReviewItem)
        if status is not None:
            stmt = stmt.where(ReviewItem.status == status)
        if case_id is not None:
            stmt = stmt.where(ReviewItem.case_id == case_id)
        stmt = stmt.order_by(ReviewItem.created_at.desc()).limit(limit).offset(offset)
        return [_review(o) for o in self.s.scalars(stmt).all()]

    def pending_count(self) -> int:
        return self.s.scalar(
            select(func.count()).select_from(ReviewItem).where(ReviewItem.status == ReviewStatus.PROPOSED)
        )

    def add(self, read: ReviewItemRead) -> ReviewItemRead:
        o = ReviewItem(
            id=read.id, item_type=read.item_type, subject_type=read.subject_type,
            subject_id=read.subject_id, case_id=read.case_id, rationale=read.rationale,
            confidence=read.confidence, evidence_ids=list(read.evidence_ids), status=read.status,
            decided_by=read.decided_by, decided_at=read.decided_at,
        )
        self.s.add(o)
        self.s.flush()
        return _review(o)

    def replace(self, read: ReviewItemRead) -> ReviewItemRead:
        o = self.s.get(ReviewItem, read.id)
        o.status = read.status
        o.decided_by = read.decided_by
        o.decided_at = read.decided_at
        self.s.flush()
        return _review(o)


class SqlAuditRepository(_Repo):
    def record(self, entry: AuditEntry) -> AuditEntry:
        o = AuditLogEntry(
            id=entry.id, actor_id=entry.actor_id, action=entry.action,
            target_type=entry.target_type, target_id=entry.target_id,
            case_id=entry.case_id, context=entry.context,
        )
        self.s.add(o)
        self.s.flush()
        return entry

    def list(self, *, case_id: UUID | None = None) -> list[AuditEntry]:
        stmt = select(AuditLogEntry)
        if case_id is not None:
            stmt = stmt.where(AuditLogEntry.case_id == case_id)
        rows = self.s.scalars(stmt.order_by(AuditLogEntry.created_at.desc())).all()
        return [_audit(o) for o in rows]


# --- unit of work ----------------------------------------------------------------


class SqlUnitOfWork:
    """Unit of work backed by a single PostgreSQL session/transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self.sources = SqlSourceRepository(session)
        self.evidence = SqlEvidenceRepository(session)
        self.entities = SqlEntityRepository(session)
        self.observations = SqlObservationRepository(session)
        self.relationships = SqlRelationshipRepository(session)
        self.clusters = SqlClusterRepository(session)
        self.cases = SqlCaseRepository(session)
        self.reports = SqlReportRepository(session)
        self.reviews = SqlReviewRepository(session)
        self.audit = SqlAuditRepository(session)
        self.graph = self._build_graph()

    @staticmethod
    def _build_graph():
        settings = get_settings()
        if settings.graph_enabled:
            from app.core.graph import get_driver
            from app.repositories.graph_repository import Neo4jGraphRepository

            return Neo4jGraphRepository(get_driver())
        from app.repositories.graph_repository import InMemoryGraphRepository

        return InMemoryGraphRepository()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def close(self) -> None:
        self._session.close()


def build_sql_unit_of_work() -> SqlUnitOfWork:
    return SqlUnitOfWork(new_session())
