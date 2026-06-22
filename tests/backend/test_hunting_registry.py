"""Hunting Grounds source/NAI registry (the authorization-first gate).

Proves the charter's invariants are enforced in code: discovery/operators only *propose*; a
source can be authorized **only from proposed** and **only with a lawful-basis record**; it can
be monitored **only after** authorization; every transition is recorded; and the lifecycle
decisions are admin-only.
"""

from __future__ import annotations

PREFIX = "/api/v1"
SRC = f"{PREFIX}/hunting/sources"

PROPOSAL = {
    "name": "Example RI listings",
    "url": "https://example.invalid/ri",
    "category": "escort_listing",
    "aor": "Rhode Island",
    "discovery_method": "operator_seed",
}
AUTH = {
    "lawful_basis": "publicly available information; licensed data agreement #RI-2026-01",
    "access_method": "licensed search API (read-only)",
    "jurisdiction": "Rhode Island, USA",
    "legal_review_note": "Reviewed by counsel 2026-06-22.",
}


def _propose(client, user="ana", **over):
    return client.post(SRC, json={**PROPOSAL, **over}, headers={"X-ORCA-User": user})


def _id(resp):
    return resp.json()["id"]


# --- propose --------------------------------------------------------------------


def test_propose_creates_a_proposed_source(client):
    resp = _propose(client)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "proposed"
    assert body["proposed_by"] == "ana"
    assert body["lawful_basis"] is None
    assert [h["to_status"] for h in body["history"]] == ["proposed"]


def test_viewer_cannot_propose(client):
    # 'vic' is a viewer — lacks CREATE_OBSERVATION.
    assert _propose(client, user="vic").status_code == 403


# --- the authorization gate -----------------------------------------------------


def test_proposed_source_is_not_authorizable_without_a_lawful_basis(client):
    sid = _id(_propose(client))
    # Missing required authorization fields → schema rejects (422).
    bad = client.post(f"{SRC}/{sid}/authorize", json={"lawful_basis": ""}, headers={"X-ORCA-User": "admin"})
    assert bad.status_code == 422


def test_authorize_records_the_basis_and_advances_status(client):
    sid = _id(_propose(client))
    resp = client.post(f"{SRC}/{sid}/authorize", json=AUTH, headers={"X-ORCA-User": "admin"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "authorized"
    assert body["lawful_basis"] == AUTH["lawful_basis"]
    assert body["authorized_by"] == "admin"
    assert body["jurisdiction"] == "Rhode Island, USA"
    assert [h["to_status"] for h in body["history"]] == ["proposed", "authorized"]


def test_non_admin_cannot_authorize(client):
    sid = _id(_propose(client))
    # An analyst proposed it but cannot authorize it (separation: the gate is admin-only).
    resp = client.post(f"{SRC}/{sid}/authorize", json=AUTH, headers={"X-ORCA-User": "ana"})
    assert resp.status_code == 403


# --- monitoring requires prior authorization ------------------------------------


def test_cannot_monitor_a_merely_proposed_source(client):
    sid = _id(_propose(client))
    resp = client.post(f"{SRC}/{sid}/monitor", headers={"X-ORCA-User": "admin"})
    assert resp.status_code == 422  # must be authorized first


def test_full_lifecycle_proposed_authorized_monitored(client):
    sid = _id(_propose(client))
    client.post(f"{SRC}/{sid}/authorize", json=AUTH, headers={"X-ORCA-User": "admin"})
    mon = client.post(f"{SRC}/{sid}/monitor", headers={"X-ORCA-User": "admin"})
    assert mon.status_code == 200
    assert mon.json()["status"] == "monitored"
    # Suspend then retire, with reasons recorded.
    admin = {"X-ORCA-User": "admin"}
    sus = client.post(f"{SRC}/{sid}/suspend", json={"reason": "rate-limit review"}, headers=admin)
    assert sus.json()["status"] == "suspended"
    ret = client.post(f"{SRC}/{sid}/retire", json={"reason": "site offline"}, headers=admin)
    assert ret.json()["status"] == "retired"
    statuses = [h["to_status"] for h in ret.json()["history"]]
    assert statuses == ["proposed", "authorized", "monitored", "suspended", "retired"]


# --- reject ---------------------------------------------------------------------


def test_reject_a_proposed_source(client):
    sid = _id(_propose(client))
    resp = client.post(f"{SRC}/{sid}/reject", json={"reason": "out of AOR"}, headers={"X-ORCA-User": "admin"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["last_decision_reason"] == "out of AOR"


# --- listing & filtering --------------------------------------------------------


def test_list_and_filter_by_status(client):
    a = _id(_propose(client, name="A"))
    _propose(client, name="B")
    client.post(f"{SRC}/{a}/authorize", json=AUTH, headers={"X-ORCA-User": "admin"})

    proposed = client.get(f"{SRC}?status=proposed", headers={"X-ORCA-User": "ana"}).json()
    authorized = client.get(f"{SRC}?status=authorized", headers={"X-ORCA-User": "ana"}).json()
    assert {s["name"] for s in proposed} == {"B"}
    assert {s["name"] for s in authorized} == {"A"}
