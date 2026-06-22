"""In-memory repository implementations over the development ``store``.

Each repository exposes the surface the service layer needs. They return Pydantic read
models directly (the store holds read models). The PostgreSQL implementations in
``app.repositories.sql`` mirror this surface.
"""

from __future__ import annotations

from uuid import UUID

from app.core.audit import AuditEntry
from app.core.rbac import MembershipStatus
from app.models.enums import EntityType, ReviewStatus
from app.repositories.base import newest_first, paginate
from app.repositories.store import InMemoryStore
from app.schemas.case import CaseRead
from app.schemas.cluster import ClusterRead
from app.schemas.entity import EntityRead
from app.schemas.evidence import EvidenceItemRead
from app.schemas.hunting import HuntingSourceRead, HuntingWatchlistEntry
from app.schemas.hunting_escalation import HuntingEscalationRead
from app.schemas.observation import ObservationRead
from app.schemas.relationship import RelationshipRead
from app.schemas.report import ReportRead
from app.schemas.report_package import ReportPackageRead
from app.schemas.review import ReviewItemRead
from app.schemas.source import SourceRead
from app.schemas.user import CaseMemberRead, UserRead


class _Base:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store


class MemorySourceRepository(_Base):
    def get(self, source_id: UUID) -> SourceRead | None:
        return self._store.sources.get(source_id)

    def list(self, *, limit: int = 50, offset: int = 0) -> list[SourceRead]:
        return paginate(newest_first(self._store.sources.values()), limit=limit, offset=offset)

    def add(self, source: SourceRead) -> SourceRead:
        self._store.sources[source.id] = source
        return source


class MemoryEvidenceRepository(_Base):
    def get(self, evidence_id: UUID) -> EvidenceItemRead | None:
        return self._store.evidence.get(evidence_id)

    def list(self, *, limit: int = 50, offset: int = 0) -> list[EvidenceItemRead]:
        return paginate(newest_first(self._store.evidence.values()), limit=limit, offset=offset)

    def for_case(self, case_id: UUID) -> list[EvidenceItemRead]:
        return newest_first(e for e in self._store.evidence.values() if e.case_id == case_id)

    def for_observation(self, observation_id: UUID) -> list[EvidenceItemRead]:
        return newest_first(
            e for e in self._store.evidence.values() if e.observation_id == observation_id
        )

    def add(self, evidence: EvidenceItemRead) -> EvidenceItemRead:
        self._store.evidence[evidence.id] = evidence
        return evidence

    def replace(self, evidence: EvidenceItemRead) -> EvidenceItemRead:
        self._store.evidence[evidence.id] = evidence
        return evidence


class MemoryEntityRepository(_Base):
    def get(self, entity_id: UUID) -> EntityRead | None:
        return self._store.entities.get(entity_id)

    def list(self, *, limit: int = 50, offset: int = 0) -> list[EntityRead]:
        return paginate(newest_first(self._store.entities.values()), limit=limit, offset=offset)

    def find_by_value(self, entity_type: EntityType, value: str) -> EntityRead | None:
        for entity in self._store.entities.values():
            if entity.entity_type == entity_type and entity.value == value:
                return entity
        return None

    def add(self, entity: EntityRead) -> EntityRead:
        self._store.entities[entity.id] = entity
        return entity


class MemoryObservationRepository(_Base):
    def get(self, observation_id: UUID) -> ObservationRead | None:
        return self._store.observations.get(observation_id)

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        case_id: UUID | None = None,
        status: ReviewStatus | None = None,
        collector: str | None = None,
    ) -> list[ObservationRead]:
        values = self._store.observations.values()
        if case_id is not None:
            values = [o for o in values if o.case_id == case_id]
        if status is not None:
            values = [o for o in values if o.status == status]
        if collector is not None:
            values = [o for o in values if o.collector == collector]
        return paginate(newest_first(values), limit=limit, offset=offset)

    def for_case(self, case_id: UUID) -> list[ObservationRead]:
        return [o for o in self._store.observations.values() if o.case_id == case_id]

    def count(self) -> int:
        return len(self._store.observations)

    def add(self, observation: ObservationRead) -> ObservationRead:
        self._store.observations[observation.id] = observation
        return observation

    def replace(self, observation: ObservationRead) -> ObservationRead:
        self._store.observations[observation.id] = observation
        return observation


class MemoryRelationshipRepository(_Base):
    def get(self, relationship_id: UUID) -> RelationshipRead | None:
        return self._store.relationships.get(relationship_id)

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        case_id: UUID | None = None,
        status: ReviewStatus | None = None,
    ) -> list[RelationshipRead]:
        values = self._store.relationships.values()
        if case_id is not None:
            values = [r for r in values if r.case_id == case_id]
        if status is not None:
            values = [r for r in values if r.status == status]
        return paginate(newest_first(values), limit=limit, offset=offset)

    def for_case(self, case_id: UUID) -> list[RelationshipRead]:
        return [r for r in self._store.relationships.values() if r.case_id == case_id]

    def count(self) -> int:
        return len(self._store.relationships)

    def add(self, relationship: RelationshipRead) -> RelationshipRead:
        self._store.relationships[relationship.id] = relationship
        return relationship

    def replace(self, relationship: RelationshipRead) -> RelationshipRead:
        self._store.relationships[relationship.id] = relationship
        return relationship


class MemoryClusterRepository(_Base):
    def get(self, cluster_id: UUID) -> ClusterRead | None:
        return self._store.clusters.get(cluster_id)

    def list(self, *, limit: int = 50, offset: int = 0) -> list[ClusterRead]:
        return paginate(newest_first(self._store.clusters.values()), limit=limit, offset=offset)

    def add(self, cluster: ClusterRead) -> ClusterRead:
        self._store.clusters[cluster.id] = cluster
        return cluster


class MemoryCaseRepository(_Base):
    def get(self, case_id: UUID) -> CaseRead | None:
        return self._store.cases.get(case_id)

    def list(self, *, limit: int = 50, offset: int = 0) -> list[CaseRead]:
        return paginate(newest_first(self._store.cases.values()), limit=limit, offset=offset)

    def add(self, case: CaseRead) -> CaseRead:
        self._store.cases[case.id] = case
        return case

    def replace(self, case: CaseRead) -> CaseRead:
        self._store.cases[case.id] = case
        return case


class MemoryReportRepository(_Base):
    def get(self, report_id: UUID) -> ReportRead | None:
        return self._store.reports.get(report_id)

    def list(self, *, case_id: UUID | None = None) -> list[ReportRead]:
        values = self._store.reports.values()
        if case_id is not None:
            values = [r for r in values if r.case_id == case_id]
        return newest_first(values)

    def list_published(self) -> list[ReportRead]:
        return newest_first(r for r in self._store.reports.values() if r.status == "final")

    def add(self, report: ReportRead) -> ReportRead:
        self._store.reports[report.id] = report
        return report

    def replace(self, report: ReportRead) -> ReportRead:
        self._store.reports[report.id] = report
        return report


class MemoryReportPackageRepository(_Base):
    def get(self, package_id: UUID) -> ReportPackageRead | None:
        return self._store.report_packages.get(package_id)

    def for_case(self, case_id: UUID) -> list[ReportPackageRead]:
        return newest_first(p for p in self._store.report_packages.values() if p.case_id == case_id)

    def list(self) -> list[ReportPackageRead]:
        return newest_first(self._store.report_packages.values())

    def add(self, package: ReportPackageRead) -> ReportPackageRead:
        self._store.report_packages[package.id] = package
        return package


class MemoryReviewRepository(_Base):
    def get(self, item_id: UUID) -> ReviewItemRead | None:
        return self._store.review_items.get(item_id)

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: ReviewStatus | None = ReviewStatus.PROPOSED,
        case_id: UUID | None = None,
    ) -> list[ReviewItemRead]:
        values = self._store.review_items.values()
        if status is not None:
            values = [i for i in values if i.status == status]
        if case_id is not None:
            values = [i for i in values if i.case_id == case_id]
        return paginate(newest_first(values), limit=limit, offset=offset)

    def pending_count(self) -> int:
        return sum(1 for i in self._store.review_items.values() if i.status == ReviewStatus.PROPOSED)

    def add(self, item: ReviewItemRead) -> ReviewItemRead:
        self._store.review_items[item.id] = item
        return item

    def replace(self, item: ReviewItemRead) -> ReviewItemRead:
        self._store.review_items[item.id] = item
        return item


class MemoryUserRepository(_Base):
    def get(self, user_id: UUID) -> UserRead | None:
        return self._store.users.get(user_id)

    def get_by_username(self, username: str) -> UserRead | None:
        for user in self._store.users.values():
            if user.username == username:
                return user
        return None

    def list(self) -> list[UserRead]:
        return sorted(self._store.users.values(), key=lambda u: u.username)

    def add(self, user: UserRead) -> UserRead:
        self._store.users[user.id] = user
        return user


class MemoryMembershipRepository(_Base):
    def for_case(self, case_id: UUID) -> list[CaseMemberRead]:
        return sorted(
            (m for m in self._store.memberships.values() if m.case_id == case_id),
            key=lambda m: m.username,
        )

    def for_user(self, user_id: UUID) -> list[CaseMemberRead]:
        return [m for m in self._store.memberships.values() if m.user_id == user_id]

    def get(self, membership_id: UUID) -> CaseMemberRead | None:
        return self._store.memberships.get(membership_id)

    def find(self, case_id: UUID, user_id: UUID) -> CaseMemberRead | None:
        """The membership for a (case, user) pair regardless of status, if any."""
        for m in self._store.memberships.values():
            if m.case_id == case_id and m.user_id == user_id:
                return m
        return None

    def get_active(self, case_id: UUID, user_id: UUID) -> CaseMemberRead | None:
        m = self.find(case_id, user_id)
        return m if m and m.status == MembershipStatus.ACTIVE else None

    def exists(self, case_id: UUID, user_id: UUID) -> bool:
        return self.find(case_id, user_id) is not None

    def add(self, member: CaseMemberRead) -> CaseMemberRead:
        self._store.memberships[member.id] = member
        return member

    def replace(self, member: CaseMemberRead) -> CaseMemberRead:
        self._store.memberships[member.id] = member
        return member


class MemoryHuntingSourceRepository(_Base):
    """Hunting Grounds source/NAI registry, over the development store (mirrors the SQL repo)."""

    def get(self, source_id: UUID) -> HuntingSourceRead | None:
        return self._store.hunting_sources.get(source_id)

    def list(self) -> list[HuntingSourceRead]:
        return list(self._store.hunting_sources.values())

    def add(self, source: HuntingSourceRead) -> HuntingSourceRead:
        self._store.hunting_sources[source.id] = source
        return source

    def replace(self, source: HuntingSourceRead) -> HuntingSourceRead:
        self._store.hunting_sources[source.id] = source
        return source


class MemoryHuntingEscalationRepository(_Base):
    """Suspected-minor / CSAM escalation channel (report-only, never-store)."""

    def get(self, escalation_id: UUID) -> HuntingEscalationRead | None:
        return self._store.hunting_escalations.get(escalation_id)

    def list(self) -> list[HuntingEscalationRead]:
        return list(self._store.hunting_escalations.values())

    def add(self, escalation: HuntingEscalationRead) -> HuntingEscalationRead:
        self._store.hunting_escalations[escalation.id] = escalation
        return escalation

    def replace(self, escalation: HuntingEscalationRead) -> HuntingEscalationRead:
        self._store.hunting_escalations[escalation.id] = escalation
        return escalation


class MemoryHuntingWatchlistRepository(_Base):
    """Operator-managed AOR watchlist (keyed by case-insensitive AOR for dedup)."""

    def list(self) -> list[HuntingWatchlistEntry]:
        return sorted(self._store.hunting_watchlist.values(), key=lambda e: e.aor.lower())

    def add(self, entry: HuntingWatchlistEntry) -> HuntingWatchlistEntry:
        self._store.hunting_watchlist[entry.aor.lower()] = entry
        return entry

    def remove(self, aor: str) -> bool:
        return self._store.hunting_watchlist.pop(aor.lower(), None) is not None


class MemoryAuditRepository(_Base):
    def record(self, entry: AuditEntry) -> AuditEntry:
        self._store.audit.append(entry)
        return entry

    def list(self, *, case_id: UUID | None = None) -> list[AuditEntry]:
        entries = list(self._store.audit)
        if case_id is not None:
            entries = [e for e in entries if e.case_id == case_id]
        return list(reversed(entries))  # newest first

    def all(self) -> list[AuditEntry]:
        return list(self._store.audit)
