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
from app.core.rbac import MembershipStatus, Role
from app.models import (
    AuditLogEntry,
    Case,
    CaseMembership,
    Cluster,
    Entity,
    EvidenceItem,
    Observation,
    Relationship,
    Report,
    ReportPackage,
    ReviewItem,
    Source,
    User,
)
from app.models.enums import EntityType, ReportStatus, ReviewStatus
from app.schemas.case import CaseRead
from app.schemas.cluster import ClusterRead
from app.schemas.entity import EntityRead
from app.schemas.evidence import EvidenceItemRead, LegalFlags
from app.schemas.handling import Handling
from app.schemas.observation import ObservationRead
from app.schemas.relationship import RelationshipRead
from app.schemas.report import ReportRead
from app.schemas.report_package import ReportPackageCounts, ReportPackageRead
from app.schemas.review import ReviewItemRead
from app.schemas.source import SourceRead
from app.schemas.user import CaseMemberRead, UserRead

# --- mappers (ORM -> read model) -------------------------------------------------


def _source(o: Source) -> SourceRead:
    return SourceRead.model_validate(o)


def _evidence(o: EvidenceItem) -> EvidenceItemRead:
    return EvidenceItemRead(
        id=o.id,
        case_id=o.case_id,
        source_id=o.source_id,
        observation_id=o.observation_id,
        title=o.title,
        description=o.description,
        evidence_type=o.evidence_type,
        storage_uri=o.storage_uri,
        original_filename=o.original_filename,
        mime_type=o.mime_type,
        size_bytes=o.size_bytes,
        sha256=o.sha256,
        captured_at=o.captured_at,
        captured_by=o.captured_by,
        access_method=o.access_method,
        legal_flags=LegalFlags(**(o.legal_flags or {})),
        handling_notes=o.handling_notes,
        status=o.status,
        has_bytes=o.has_bytes,
        created_by=o.created_by,
        created_at=o.created_at,
    )


def _entity(o: Entity) -> EntityRead:
    return EntityRead.model_validate(o)


def _case(o: Case) -> CaseRead:
    return CaseRead.model_validate(o)


def _report(o: Report) -> ReportRead:
    return ReportRead.model_validate(o)


def _review(o: ReviewItem) -> ReviewItemRead:
    return ReviewItemRead.model_validate(o)


def _report_package(o: ReportPackage) -> ReportPackageRead:
    counts = (o.manifest or {}).get("counts", {})
    return ReportPackageRead(
        id=o.id,
        case_id=o.case_id,
        title=o.title,
        status=o.status,
        handling_level=o.handling_level,
        generated_by=o.generated_by,
        counts=ReportPackageCounts(
            approved_observations=counts.get("approved_observations", 0),
            approved_relationships=counts.get("approved_relationships", 0),
            cited_evidence=counts.get("cited_evidence", 0),
        ),
        caveats=list((o.manifest or {}).get("caveats", [])),
        report_sha256=o.report_sha256,
        manifest_sha256=o.manifest_sha256,
        report_markdown=o.report_markdown,
        manifest=o.manifest,
        created_at=o.created_at,
    )


def _user(o: User) -> UserRead:
    return UserRead.model_validate(o)


def _membership(o: CaseMembership, user: User | None) -> CaseMemberRead:
    return CaseMemberRead(
        id=o.id,
        case_id=o.case_id,
        user_id=o.user_id,
        username=user.username if user else "",
        display_name=user.display_name if user else "",
        global_role=user.role if user else Role.VIEWER,
        case_role=o.case_role,
        status=o.status,
        assigned_by=o.assigned_by,
        assigned_at=o.assigned_at,
        notes=o.notes,
        created_at=o.created_at,
        updated_at=o.updated_at,
    )


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
    def get(self, evidence_id: UUID) -> EvidenceItemRead | None:
        o = self.s.get(EvidenceItem, evidence_id)
        return _evidence(o) if o else None

    def list(self, *, limit: int = 50, offset: int = 0) -> list[EvidenceItemRead]:
        rows = self.s.scalars(
            select(EvidenceItem).order_by(EvidenceItem.created_at.desc()).limit(limit).offset(offset)
        ).all()
        return [_evidence(o) for o in rows]

    def for_case(self, case_id: UUID) -> list[EvidenceItemRead]:
        rows = self.s.scalars(
            select(EvidenceItem)
            .where(EvidenceItem.case_id == case_id)
            .order_by(EvidenceItem.created_at.desc())
        ).all()
        return [_evidence(o) for o in rows]

    def for_observation(self, observation_id: UUID) -> list[EvidenceItemRead]:
        rows = self.s.scalars(
            select(EvidenceItem).where(EvidenceItem.observation_id == observation_id)
        ).all()
        return [_evidence(o) for o in rows]

    def add(self, read: EvidenceItemRead) -> EvidenceItemRead:
        o = EvidenceItem(
            id=read.id, case_id=read.case_id, source_id=read.source_id,
            observation_id=read.observation_id, title=read.title, description=read.description,
            evidence_type=read.evidence_type, storage_uri=read.storage_uri,
            original_filename=read.original_filename, mime_type=read.mime_type,
            size_bytes=read.size_bytes, sha256=read.sha256, captured_at=read.captured_at,
            captured_by=read.captured_by, access_method=read.access_method,
            legal_flags=read.legal_flags.model_dump(), handling_notes=read.handling_notes,
            status=read.status, has_bytes=read.has_bytes, created_by=read.created_by,
        )
        self.s.add(o)
        self.s.flush()
        return _evidence(o)

    def replace(self, read: EvidenceItemRead) -> EvidenceItemRead:
        o = self.s.get(EvidenceItem, read.id)
        o.observation_id = read.observation_id
        o.status = read.status
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

    def list_published(self) -> list[ReportRead]:
        rows = self.s.scalars(
            select(Report).where(Report.status == ReportStatus.FINAL).order_by(Report.created_at.desc())
        ).all()
        return [_report(o) for o in rows]

    def add(self, read: ReportRead) -> ReportRead:
        o = Report(
            id=read.id, case_id=read.case_id, title=read.title, author=read.author,
            status=read.status, body=read.body,
        )
        self.s.add(o)
        self.s.flush()
        return _report(o)

    def replace(self, read: ReportRead) -> ReportRead:
        o = self.s.get(Report, read.id)
        o.status = read.status
        o.title = read.title
        o.body = read.body
        self.s.flush()
        return _report(o)


class SqlUserRepository(_Repo):
    def get(self, user_id: UUID) -> UserRead | None:
        o = self.s.get(User, user_id)
        return _user(o) if o else None

    def get_by_username(self, username: str) -> UserRead | None:
        o = self.s.scalars(select(User).where(User.username == username)).first()
        return _user(o) if o else None

    def list(self) -> list[UserRead]:
        return [_user(o) for o in self.s.scalars(select(User).order_by(User.username)).all()]

    def add(self, read: UserRead) -> UserRead:
        o = User(id=read.id, username=read.username, display_name=read.display_name, role=read.role)
        self.s.add(o)
        self.s.flush()
        return _user(o)


class SqlMembershipRepository(_Repo):
    def _read(self, o: CaseMembership) -> CaseMemberRead:
        return _membership(o, self.s.get(User, o.user_id))

    def for_case(self, case_id: UUID) -> list[CaseMemberRead]:
        rows = self.s.scalars(
            select(CaseMembership).where(CaseMembership.case_id == case_id)
        ).all()
        return sorted((self._read(m) for m in rows), key=lambda m: m.username)

    def for_user(self, user_id: UUID) -> list[CaseMemberRead]:
        rows = self.s.scalars(
            select(CaseMembership).where(CaseMembership.user_id == user_id)
        ).all()
        return [self._read(m) for m in rows]

    def get(self, membership_id: UUID) -> CaseMemberRead | None:
        o = self.s.get(CaseMembership, membership_id)
        return self._read(o) if o else None

    def _row(self, case_id: UUID, user_id: UUID) -> CaseMembership | None:
        return self.s.scalars(
            select(CaseMembership).where(
                CaseMembership.case_id == case_id, CaseMembership.user_id == user_id
            )
        ).first()

    def find(self, case_id: UUID, user_id: UUID) -> CaseMemberRead | None:
        o = self._row(case_id, user_id)
        return self._read(o) if o else None

    def get_active(self, case_id: UUID, user_id: UUID) -> CaseMemberRead | None:
        o = self.s.scalars(
            select(CaseMembership).where(
                CaseMembership.case_id == case_id,
                CaseMembership.user_id == user_id,
                CaseMembership.status == MembershipStatus.ACTIVE,
            )
        ).first()
        return self._read(o) if o else None

    def exists(self, case_id: UUID, user_id: UUID) -> bool:
        return self._row(case_id, user_id) is not None

    def add(self, member: CaseMemberRead) -> CaseMemberRead:
        o = CaseMembership(
            id=member.id, case_id=member.case_id, user_id=member.user_id,
            case_role=member.case_role, status=member.status,
            assigned_by=member.assigned_by, assigned_at=member.assigned_at, notes=member.notes,
        )
        self.s.add(o)
        self.s.flush()
        return self._read(o)

    def replace(self, member: CaseMemberRead) -> CaseMemberRead:
        o = self.s.get(CaseMembership, member.id)
        o.case_role = member.case_role
        o.status = member.status
        o.notes = member.notes
        o.assigned_by = member.assigned_by
        o.assigned_at = member.assigned_at
        self.s.flush()
        return self._read(o)


class SqlReportPackageRepository(_Repo):
    def get(self, package_id: UUID) -> ReportPackageRead | None:
        o = self.s.get(ReportPackage, package_id)
        return _report_package(o) if o else None

    def for_case(self, case_id: UUID) -> list[ReportPackageRead]:
        rows = self.s.scalars(
            select(ReportPackage)
            .where(ReportPackage.case_id == case_id)
            .order_by(ReportPackage.created_at.desc())
        ).all()
        return [_report_package(o) for o in rows]

    def list(self) -> list[ReportPackageRead]:
        rows = self.s.scalars(
            select(ReportPackage).order_by(ReportPackage.created_at.desc())
        ).all()
        return [_report_package(o) for o in rows]

    def add(self, read: ReportPackageRead) -> ReportPackageRead:
        o = ReportPackage(
            id=read.id, case_id=read.case_id, title=read.title, status=read.status,
            handling_level=read.handling_level, generated_by=read.generated_by,
            report_markdown=read.report_markdown, manifest=read.manifest,
            report_sha256=read.report_sha256, manifest_sha256=read.manifest_sha256,
        )
        self.s.add(o)
        self.s.flush()
        return _report_package(o)


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
            subject_id=read.subject_id, case_id=read.case_id, created_by=read.created_by,
            rationale=read.rationale, confidence=read.confidence,
            evidence_ids=list(read.evidence_ids), status=read.status,
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
        self.report_packages = SqlReportPackageRepository(session)
        self.reviews = SqlReviewRepository(session)
        self.users = SqlUserRepository(session)
        self.memberships = SqlMembershipRepository(session)
        self.audit = SqlAuditRepository(session)
        self.graph = self._build_graph()
        from app.core.content_store import build_content_store

        self.content = build_content_store()

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
