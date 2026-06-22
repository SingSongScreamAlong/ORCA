"""Hunting Grounds persistence — the registry and escalation channel go through the unit of
work (durable across restarts on PostgreSQL), not a bare module global.

The SQL backend stores each record as a JSONB ``document`` and rebuilds the read model with
``HuntingSourceRead.model_validate(document)``. That round-trip is the persistence contract, so
these tests pin it down on the in-memory path (which CI runs) — if a schema change broke the
JSON round-trip, the SQL backend would silently corrupt records. They also exercise the repo
surface (get/list/add/replace) the unit of work now exposes.
"""

from __future__ import annotations

from app.repositories.uow import build_unit_of_work
from app.schemas.hunting import HuntingSourceRead
from app.schemas.hunting_escalation import HuntingEscalationRead

PREFIX = "/api/v1"
SRC = f"{PREFIX}/hunting/sources"
ADMIN = {"X-ORCA-User": "admin"}
ANA = {"X-ORCA-User": "ana"}

AUTH = {
    "lawful_basis": "publicly available; licensed feed #RI-2026-03",
    "access_method": "licensed search API (read-only)",
    "jurisdiction": "Rhode Island, USA",
    "legal_review_note": "Reviewed by counsel 2026-06-22.",
}


# --- the JSONB document round-trip (the SQL persistence contract) ----------------


def test_source_document_round_trips(client):
    proposal = {
        "name": "RI listings",
        "url": "https://ri.invalid/x",
        "category": "escort_listing",
        "aor": "Rhode Island",
    }
    sid = client.post(SRC, json=proposal, headers=ANA).json()["id"]
    client.post(f"{SRC}/{sid}/authorize", json=AUTH, headers=ADMIN)
    source = client.get(f"{SRC}/{sid}", headers=ANA).json()

    model = HuntingSourceRead.model_validate(source)
    # This is exactly what SqlHuntingSourceRepository stores and re-reads.
    assert HuntingSourceRead.model_validate(model.model_dump(mode="json")) == model
    # The nested append-only history survives the round-trip.
    assert [h.to_status.value for h in model.history] == ["proposed", "authorized"]


def test_escalation_document_round_trips(client):
    esc = client.post(
        f"{PREFIX}/hunting/escalations",
        json={"aor": "Rhode Island", "concern": "Appears to depict a minor."},
        headers=ANA,
    ).json()
    model = HuntingEscalationRead.model_validate(esc)
    assert HuntingEscalationRead.model_validate(model.model_dump(mode="json")) == model


# --- the unit-of-work repository surface ----------------------------------------


def test_uow_exposes_hunting_repositories(client):
    # Propose through the API, then confirm the registry repo on a fresh unit of work sees it
    # (persistence is via the uow/store, not a service-local global).
    sid = client.post(
        SRC,
        json={"name": "S", "url": "https://s.invalid", "category": "forum", "aor": "Maine"},
        headers=ANA,
    ).json()["id"]

    uow = build_unit_of_work()
    listed = uow.hunting_sources.list()
    assert any(str(s.id) == sid for s in listed)
    fetched = uow.hunting_sources.get(next(s.id for s in listed if str(s.id) == sid))
    assert fetched is not None and fetched.name == "S"
    assert uow.hunting_escalations.list() == []


def test_memory_repo_replace_updates_in_place(client):
    from app.schemas.hunting import HuntingSourcePropose
    from app.services.hunting_registry_service import HuntingRegistryService

    uow = build_unit_of_work()
    svc = HuntingRegistryService(uow)
    from app.core.security import Principal
    from app.models.user import Role

    principal = Principal(id="ana", username="ana", display_name="Ana", role=Role.ANALYST)
    src = svc.propose(
        HuntingSourcePropose(name="R", url="https://r.invalid", aor="Rhode Island"), principal
    )
    rejected = svc.reject(src.id, "out of AOR", principal)
    assert rejected.status.value == "rejected"
    # The stored record reflects the transition (replace, not a duplicate insert).
    again = uow.hunting_sources.get(src.id)
    assert again.status.value == "rejected"
    assert len(uow.hunting_sources.list()) == 1
