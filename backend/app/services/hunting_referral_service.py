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
from app.models.enums import EntityType
from app.repositories.uow import UnitOfWork
from app.schemas.entity import EntityRead
from app.schemas.hunting import (
    AorReferralPackage,
    HuntingReferralPackage,
    HuntingReferralRecord,
    IdentifierReferralPackage,
    OperationReferralPackage,
    ReferralEntity,
    ReferralObservation,
    ReferralRelationship,
    ReferralSource,
)
from app.services.hunting_intel_service import HuntingIntelService
from app.services.hunting_lead_service import hunting_collector_marker
from app.services.hunting_registry_service import HuntingRegistryService

_MAX = 1000  # recon scale; a source's lead volume is small relative to the case store


class HuntingReferralService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def referral_history(self, limit: int = 100) -> list[HuntingReferralRecord]:
        """The accountability view: what was handed to LE, at what scope, by whom, and when.

        Reads the append-only audit trail (``hunting.referral.*``, newest first) — the records say a
        dossier was generated, never its contents. Counts and pointers only.
        """
        names = {str(u.id): u.username for u in self.uow.users.list()}  # show the author, not a UUID
        records: list[HuntingReferralRecord] = []
        for entry in self.uow.audit.list():  # newest first
            tier = _REFERRAL_TIER.get(entry.action)  # only known referral actions, never a default
            if tier is None:
                continue
            by = names.get(entry.actor_id, entry.actor_id)
            records.append(_to_referral_record(entry, by, tier))
            if len(records) >= limit:
                break
        return records

    def build(self, source_id: UUID, principal: Principal) -> HuntingReferralPackage:
        source = HuntingRegistryService(self.uow).get(source_id)  # 404 if missing

        # The text leads located from this source (proposed/approved observations alike). Filter
        # by collector at the repository so the cap applies to *this source's* leads, not globally.
        marker = hunting_collector_marker(source.id)
        observations = self.uow.observations.list(collector=marker, limit=_MAX)
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

        # Cross-venue intelligence: how many monitored venues each located identifier appears in
        # (>=2 ⇒ a cross-venue link, the strongest lead). Computed across all monitored sources.
        intel = HuntingIntelService(self.uow)
        venue_index = intel.entity_source_index(intel.monitored_sources())
        located = [
            ReferralEntity(
                entity_type=e.entity_type,
                value=e.value,
                venue_count=max(1, len(venue_index.get(e.id, ()))),
            )
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
        ref_source = _to_referral_source(source)
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

    def build_for_identifier(
        self, entity_type: EntityType, value: str, principal: Principal
    ) -> IdentifierReferralPackage | None:
        """The per-identifier referral: assemble the cross-venue case file for one located
        identifier — every monitored venue it appears in (with lawful basis), the text leads, the
        identifiers it co-occurs with, and the relationships among them. ``None`` if never located.

        Complements :meth:`build` (per-venue): this is the dossier for one phone/wallet/handle/
        ``.onion`` across the whole hunting ground. Pointers and metadata only — no media. Audited.
        """
        intel = HuntingIntelService(self.uow)
        dossier = intel.identifier_dossier(entity_type, value)
        if dossier is None:
            return None
        subject = self.uow.entities.find_by_value(entity_type, value)  # resolved (dossier non-None)

        # The distinct venues it was located from (in first-seen order), each with its lawful basis.
        source_by_id = {s.id: s for s in intel.monitored_sources()}
        seen_ids: list[UUID] = []
        for a in dossier.appearances:
            if a.source_id not in seen_ids:
                seen_ids.append(a.source_id)
        sources = [_to_referral_source(source_by_id[sid]) for sid in seen_ids if sid in source_by_id]

        # Relationships among the identifier and the identifiers it co-occurs with.
        cited = {subject.id}
        for c in dossier.co_occurring:
            entity = self.uow.entities.find_by_value(c.entity_type, c.value)
            if entity is not None:
                cited.add(entity.id)
        relationships = self._relationships_among(cited)

        now = datetime.now(UTC)
        package = IdentifierReferralPackage(
            entity_type=dossier.entity_type,
            value=dossier.value,
            generated_at=now,
            generated_by=principal.username,
            venue_count=dossier.venue_count,
            lead_count=dossier.lead_count,
            aors=dossier.aors,
            sources=sources,
            appearances=dossier.appearances,
            co_occurring=dossier.co_occurring,
            relationships=relationships,
            summary_markdown=_render_identifier_markdown(dossier, sources, relationships, now),
        )
        self._audit_identifier(principal, package)
        return package

    def _audit_identifier(self, principal: Principal, package: IdentifierReferralPackage) -> None:
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="hunting.referral.identifier_generated",
                target_type="hunting_identifier",
                target_id=f"{package.entity_type.value}:{package.value}",
                case_id=None,
                context={
                    "identifier": package.value,
                    "type": package.entity_type.value,
                    "venues": package.venue_count,
                    "leads": package.lead_count,
                },
            )
        )

    def _relationships_among(self, cited: set[UUID]) -> list[ReferralRelationship]:
        """The relationships ORCA proposed/confirmed touching any of the cited identifiers."""
        relationships: list[ReferralRelationship] = []
        for rel in self.uow.relationships.list(limit=_MAX):
            if rel.source_entity_id in cited or rel.target_entity_id in cited:
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
        return relationships

    def build_for_aor(self, aor: str, principal: Principal) -> AorReferralPackage:
        """The AOR operation rollup: consolidate a whole region into one LE dossier — every
        monitored venue (with lawful basis), all located identifiers (cross-venue ones flagged),
        the cross-venue links tying venues into one operation, and the relationship map.

        Composes the per-venue and per-identifier referrals at AOR scope. Always returns a package
        (possibly empty when nothing is monitored/located). Pointers and metadata only — no media.
        Audited.
        """
        intel = HuntingIntelService(self.uow)
        sources = intel.monitored_sources(aor)
        picture = intel.picture(aor)
        venue_index = intel.entity_source_index(sources)  # within-AOR venue counts

        # The located identifiers across the AOR's venues (deduped, first-seen order), plus leads.
        entity_ids: list[UUID] = []
        entities_by_id: dict[UUID, EntityRead] = {}
        lead_count = 0
        for source in sources:
            marker = hunting_collector_marker(source.id)
            observations = self.uow.observations.list(collector=marker, limit=_MAX)
            lead_count += len(observations)
            for obs in observations:
                for eid in obs.entity_ids:
                    if eid not in entities_by_id:
                        entity = self.uow.entities.get(eid)
                        if entity is not None:
                            entities_by_id[eid] = entity
                            entity_ids.append(eid)

        located = [
            ReferralEntity(
                entity_type=e.entity_type,
                value=e.value,
                venue_count=max(1, len(venue_index.get(e.id, ()))),
            )
            for e in (entities_by_id[i] for i in entity_ids)
        ]
        relationships = self._relationships_among(set(entity_ids))

        now = datetime.now(UTC)
        package = AorReferralPackage(
            aor=aor,
            generated_at=now,
            generated_by=principal.username,
            source_count=len(sources),
            identifier_count=len(located),
            lead_count=lead_count,
            cross_venue_count=picture.cross_venue_count,
            sources=[_to_referral_source(s) for s in sources],
            located_identifiers=located,
            cross_venue=picture.cross_venue,
            relationships=relationships,
            summary_markdown=_render_aor_markdown(
                aor, [_to_referral_source(s) for s in sources], located,
                picture.cross_venue, relationships, lead_count, now,
            ),
        )
        self._audit_aor(principal, package)
        return package

    def _audit_aor(self, principal: Principal, package: AorReferralPackage) -> None:
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="hunting.referral.aor_generated",
                target_type="hunting_aor",
                target_id=package.aor,
                case_id=None,
                context={
                    "aor": package.aor,
                    "sources": package.source_count,
                    "identifiers": package.identifier_count,
                    "cross_venue": package.cross_venue_count,
                },
            )
        )

    def build_for_operation(
        self, entity_type: EntityType, value: str, principal: Principal
    ) -> OperationReferralPackage | None:
        """The per-operation referral: wrap the connected-component cluster around a seed identifier
        into an LE dossier — its member identifiers, the venues (with lawful basis), the relationship
        map, and a markdown summary. ``None`` if the seed was never located.

        Bounds the case by the actual linked network rather than by region (the AOR rollup) or a
        single identifier. Pointers and metadata only — no media. Audited.
        """
        cluster = HuntingIntelService(self.uow).operation_cluster(entity_type, value)
        if cluster is None:
            return None
        now = datetime.now(UTC)
        package = OperationReferralPackage(
            seed_type=cluster.seed_type,
            seed_value=cluster.seed_value,
            generated_at=now,
            generated_by=principal.username,
            identifier_count=cluster.identifier_count,
            venue_count=cluster.venue_count,
            lead_count=cluster.lead_count,
            aors=cluster.aors,
            members=cluster.members,
            venues=cluster.venues,
            relationships=cluster.relationships,
            truncated=cluster.truncated,
            summary_markdown=_render_operation_markdown(cluster, now),
        )
        self._audit_operation(principal, package)
        return package

    def _audit_operation(self, principal: Principal, package: OperationReferralPackage) -> None:
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="hunting.referral.operation_generated",
                target_type="hunting_operation",
                target_id=f"{package.seed_type.value}:{package.seed_value}",
                case_id=None,
                context={
                    "seed": package.seed_value,
                    "type": package.seed_type.value,
                    "identifiers": package.identifier_count,
                    "venues": package.venue_count,
                },
            )
        )

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


def _to_referral_source(source) -> ReferralSource:
    return ReferralSource.from_source(source)


_REFERRAL_TIER = {
    "hunting.referral.generated": "source",
    "hunting.referral.identifier_generated": "identifier",
    "hunting.referral.aor_generated": "aor",
    "hunting.referral.operation_generated": "operation",
}


def _to_referral_record(entry, by: str, tier: str) -> HuntingReferralRecord:
    ctx = entry.context or {}
    if tier == "source":
        target = ctx.get("source") or entry.target_id
        summary = f"{ctx.get('identifiers', 0)} identifiers · {ctx.get('observations', 0)} leads"
    elif tier == "identifier":
        target = f"{ctx.get('type', '')} {ctx.get('identifier', entry.target_id)}".strip()
        summary = f"{ctx.get('venues', 0)} venues · {ctx.get('leads', 0)} leads"
    elif tier == "aor":
        target = ctx.get("aor") or entry.target_id
        summary = (
            f"{ctx.get('sources', 0)} venues · {ctx.get('identifiers', 0)} identifiers"
            f" · {ctx.get('cross_venue', 0)} cross-venue"
        )
    else:  # operation
        target = f"{ctx.get('type', '')} {ctx.get('seed', entry.target_id)}".strip()
        summary = f"{ctx.get('identifiers', 0)} identifiers · {ctx.get('venues', 0)} venues"
    return HuntingReferralRecord(
        tier=tier,
        target=target,
        target_type=entry.target_type,
        generated_by=by,
        generated_at=entry.created_at,
        summary=summary,
    )


def _render_operation_markdown(cluster, now) -> str:
    lines = [
        f"# Operation dossier — seed {cluster.seed_value}",
        "",
        "_Lawful OSINT referral. Pointers and metadata only — no media. Identifiers are leads for "
        "lawful follow-up; de-anonymization requires legal process._",
        "",
        "## Operation",
        f"- **Seed identifier:** `{cluster.seed_type.value}` {cluster.seed_value}",
        f"- **Linked identifiers:** {cluster.identifier_count} · **Venues:** {cluster.venue_count}"
        f" · **Leads:** {cluster.lead_count}",
        f"- **AORs spanned:** {', '.join(cluster.aors) or '—'}",
    ]
    if cluster.truncated:
        lines.append("- **Note:** network truncated at the traversal cap — a very large operation.")
    lines += [
        f"- **Generated:** {now.isoformat()}",
        "",
        f"## Member identifiers ({len(cluster.members)})",
    ]
    if cluster.members:
        lines += [
            f"- `{m.entity_type.value}` — {m.value}  ({m.venue_count} venue(s), {m.lead_count} lead(s))"
            for m in cluster.members
        ]
    else:
        lines.append("- (none)")
    lines += ["", f"## Venues / provenance ({len(cluster.venues)})"]
    if cluster.venues:
        for s in cluster.venues:
            lines.append(
                f"- **{s.name}** (`{s.url}`) — AOR {s.aor} · {s.category.value}"
                f" · status {s.status.value}"
            )
            lines.append(
                f"  - Lawful basis: {s.lawful_basis or '—'} · Access: {s.access_method or '—'}"
                f" · Jurisdiction: {s.jurisdiction or '—'}"
            )
    else:
        lines.append("- (none)")
    lines += ["", f"## Relationships ({len(cluster.relationships)})"]
    if cluster.relationships:
        lines += [
            f"- {r.source_value} —[{r.relationship_type}]→ {r.target_value} "
            f"(confidence {r.confidence:.2f}, {r.status})"
            for r in cluster.relationships
        ]
    else:
        lines.append("- (none)")
    return "\n".join(lines)


def _render_aor_markdown(aor, sources, identifiers, cross_venue, relationships, lead_count, now) -> str:
    cross = sorted(identifiers, key=lambda i: i.venue_count, reverse=True)
    lines = [
        f"# Operation rollup — {aor}",
        "",
        "_Lawful OSINT referral. Pointers and metadata only — no media. Identifiers are leads for "
        "lawful follow-up; de-anonymization requires legal process._",
        "",
        "## Scope",
        f"- **AOR:** {aor}",
        f"- **Monitored venues:** {len(sources)} · **Located identifiers:** {len(identifiers)}"
        f" · **Text leads:** {lead_count}",
        f"- **Cross-venue links (≥2 venues):** {len(cross_venue)} — the strongest signal that "
        "separate venues are one operation.",
        f"- **Generated:** {now.isoformat()}",
        "",
        f"## Monitored venues / provenance ({len(sources)})",
    ]
    if sources:
        for s in sources:
            lines.append(
                f"- **{s.name}** (`{s.url}`) — {s.category.value} · status {s.status.value}"
            )
            lines.append(
                f"  - Lawful basis: {s.lawful_basis or '—'} · Access: {s.access_method or '—'}"
                f" · Jurisdiction: {s.jurisdiction or '—'}"
            )
    else:
        lines.append("- (none monitored in this AOR)")
    lines += ["", f"## Cross-venue links ({len(cross_venue)})"]
    if cross_venue:
        lines += [
            f"- `{i.entity_type.value}` — {i.value}  **({i.source_count} venues, {i.lead_count} leads)**"
            for i in cross_venue
        ]
    else:
        lines.append("- (none yet — located identifiers so far appear in a single venue)")
    lines += ["", f"## Located identifiers ({len(identifiers)})"]
    if identifiers:
        lines += [
            f"- `{i.entity_type.value}` — {i.value}"
            + (f"  (cross-venue: {i.venue_count} venues)" if i.venue_count >= 2 else "")
            for i in cross
        ]
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
    return "\n".join(lines)


def _render_identifier_markdown(dossier, sources, relationships, now) -> str:
    lines = [
        f"# Referral dossier — identifier {dossier.value}",
        "",
        "_Lawful OSINT referral. Pointers and metadata only — no media. Identifiers are leads for "
        "lawful follow-up; de-anonymization requires legal process._",
        "",
        "## Subject identifier",
        f"- **Type:** `{dossier.entity_type.value}` · **Value:** {dossier.value}",
        f"- **Located in:** {dossier.venue_count} venue(s) across {len(dossier.aors)} AOR(s)"
        f" ({', '.join(dossier.aors) or '—'})",
        f"- **Text leads citing it:** {dossier.lead_count}",
        f"- **Generated:** {now.isoformat()}",
        "",
        f"## Venues / provenance ({len(sources)})",
    ]
    if sources:
        for s in sources:
            lines.append(
                f"- **{s.name}** (`{s.url}`) — AOR {s.aor} · {s.category.value}"
                f" · status {s.status.value}"
            )
            lines.append(
                f"  - Lawful basis: {s.lawful_basis or '—'} · Access: {s.access_method or '—'}"
                f" · Jurisdiction: {s.jurisdiction or '—'}"
            )
    else:
        lines.append("- (none)")
    lines += ["", f"## Text leads ({len(dossier.appearances)})"]
    if dossier.appearances:
        lines += [
            f"- {a.observed_at.date()} — [{a.source_name}] {a.summary}" for a in dossier.appearances
        ]
    else:
        lines.append("- (none)")
    lines += ["", f"## Co-occurring identifiers ({len(dossier.co_occurring)})"]
    if dossier.co_occurring:
        lines += [
            f"- `{c.entity_type.value}` — {c.value}  (shares {c.shared_leads} lead(s))"
            for c in dossier.co_occurring
        ]
    else:
        lines.append("- (none)")
    lines += ["", f"## Relationships ({len(relationships)})"]
    if relationships:
        lines += [
            f"- {r.source_value} —[{r.relationship_type}]→ {r.target_value} "
            f"(confidence {r.confidence:.2f}, {r.status})"
            for r in relationships
        ]
    else:
        lines.append("- (none)")
    return "\n".join(lines)


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
        lines += [
            f"- `{i.entity_type.value}` — {i.value}"
            + (f"  **(cross-venue: {i.venue_count} venues)**" if i.venue_count >= 2 else "")
            for i in identifiers
        ]
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
