"""Hunting Grounds → law enforcement referral dossier.

The "locate → case" output. Given a monitored source, this aggregates everything ORCA *located*
from it — the text leads, the extracted identifiers (phones, emails, crypto, ``.onion``, URLs,
handles), and the relationship map linking them — together with the source's provenance and the
lawful basis it was watched under. The result is a referral package an analyst can hand to law
enforcement to support a Project 1591 case.

By construction it contains **no media** — only pointers and metadata. It does not unmask anyone:
identifiers are leads for lawful follow-up; turning a handle into a person is law enforcement's
job, with legal process. Generating a referral is a privileged action and is audited.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.audit import new_audit_entry
from app.core.security import Principal
from app.repositories.uow import UnitOfWork
from app.schemas.hunting import (
    HuntingReferralPackage,
    ReferralEntity,
    ReferralObservation,
    ReferralRelationship,
    ReferralSource,
)
from app.services.hunting_registry_service import HuntingRegistryService

_MAX = 1000  # recon scale; a source's lead volume is small relative to the case store


def _marker(source_name: str) -> str:
    # The lead service stamps observations from a hunting source with this collector.
    return f"hunting-grounds:{source_name}"


class HuntingReferralService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def build(self, source_id: UUID, principal: Principal) -> HuntingReferralPackage:
        source = HuntingRegistryService(self.uow).get(source_id)  # 404 if missing

        # The text leads located from this source (proposed/approved observations alike).
        marker = _marker(source.name)
        observations = [
            o for o in self.uow.observations.list(limit=_MAX) if o.collector == marker
        ]
        observations.sort(key=lambda o: o.timestamp)

        # The located identifiers across those leads (deduped), and the lookup for relationships.
        entity_ids: list[UUID] = []
        entities_by_id = {}
        for obs in observations:
            for eid in obs.entity_ids:
                if eid not in entities_by_id:
                    entity = self.uow.entities.get(eid)
                    if entity is not None:
                        entities_by_id[eid] = entity
                        entity_ids.append(eid)
        located = [
            ReferralEntity(entity_type=e.entity_type, value=e.value)
            for e in (entities_by_id[i] for i in entity_ids)
        ]

        # Relationships ORCA proposed/confirmed among those identifiers.
        in_set = set(entity_ids)
        relationships = []
        for rel in self.uow.relationships.list(limit=_MAX):
            if rel.source_entity_id in in_set or rel.target_entity_id in in_set:
                s = entities_by_id.get(rel.source_entity_id) or self.uow.entities.get(rel.source_entity_id)
                t = entities_by_id.get(rel.target_entity_id) or self.uow.entities.get(rel.target_entity_id)
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

        obs_models = [
            ReferralObservation(
                id=o.id, summary=o.notes or "", observed_at=o.timestamp,
                confidence=o.confidence, status=o.status.value,
            )
            for o in observations
        ]
        ref_source = ReferralSource(
            id=source.id, name=source.name, url=source.url, category=source.category,
            aor=source.aor, status=source.status, lawful_basis=source.lawful_basis,
            access_method=source.access_method, jurisdiction=source.jurisdiction,
            proposed_by=source.proposed_by, authorized_by=source.authorized_by,
        )
        now = datetime.now(UTC)
        package = HuntingReferralPackage(
            source=ref_source,
            generated_at=now,
            generated_by=principal.username,
            observation_count=len(obs_models),
            identifier_count=len(located),
            located_identifiers=located,
            observations=obs_models,
            relationships=relationships,
            summary_markdown=_render_markdown(ref_source, located, obs_models, relationships, now),
        )
        self._audit(principal, source.id, package)
        return package

    def _audit(self, principal: Principal, source_id: UUID, package: HuntingReferralPackage) -> None:
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="hunting.referral.generated",
                target_type="hunting_source",
                target_id=source_id,
                case_id=None,
                context={
                    "source": package.source.name,
                    "identifiers": package.identifier_count,
                    "observations": package.observation_count,
                },
            )
        )


def _render_markdown(source, identifiers, observations, relationships, now) -> str:
    lines = [
        f"# Referral dossier — {source.name}",
        "",
        "_Lawful OSINT referral. Pointers and metadata only — no media. Identifiers are leads for "
        "lawful follow-up; de-anonymization requires legal process._",
        "",
        "## Source / provenance",
        f"- **Venue:** {source.name} (`{source.url}`)",
        f"- **AOR:** {source.aor} · **Category:** {source.category.value}"
        f" · **Status:** {source.status.value}",
        f"- **Lawful basis:** {source.lawful_basis or '—'}",
        f"- **Access method:** {source.access_method or '—'}"
        f" · **Jurisdiction:** {source.jurisdiction or '—'}",
        f"- **Proposed by:** {source.proposed_by} · **Authorized by:** {source.authorized_by or '—'}",
        f"- **Generated:** {now.isoformat()}",
        "",
        f"## Located identifiers ({len(identifiers)})",
    ]
    if identifiers:
        lines += [f"- `{i.entity_type.value}` — {i.value}" for i in identifiers]
    else:
        lines.append("- (none located yet)")
    lines += ["", f"## Relationships ({len(relationships)})"]
    if relationships:
        lines += [
            f"- {r.source_value} —[{r.relationship_type}]→ {r.target_value} "
            f"(confidence {r.confidence:.2f}, {r.status})"
            for r in relationships
        ]
    else:
        lines.append("- (none)")
    lines += ["", f"## Text leads ({len(observations)})"]
    if observations:
        lines += [f"- {o.observed_at.date()} — {o.summary}" for o in observations]
    else:
        lines.append("- (none)")
    return "\n".join(lines)
