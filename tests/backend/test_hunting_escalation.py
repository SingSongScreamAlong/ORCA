"""Suspected-minor / CSAM escalation — the charter's report-only, never-store hard-stop.

Proves: any operator can raise a concern; it stores no material (only a pointer/concern note);
the lifecycle open → reported → closed (and open → dismissed) is enforced; listing and the
report/close/dismiss decisions are admin-only.
"""

from __future__ import annotations

PREFIX = "/api/v1"
ESC = f"{PREFIX}/hunting/escalations"

RAISE = {
    "aor": "Rhode Island",
    "url": "https://example.invalid/listing/123",
    "concern": "Listing appears to depict a minor.",
}


def _raise(client, user="ana", **over):
    return client.post(ESC, json={**RAISE, **over}, headers={"X-ORCA-User": user})


def _id(resp):
    return resp.json()["id"]


def test_operator_can_raise_a_concern_open(client):
    resp = _raise(client)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "open"
    assert body["raised_by"] == "ana"
    assert body["ncmec_reference"] is None
    # No material is stored — only the concern pointer the operator wrote.
    assert body["concern"] == RAISE["concern"]
    assert [h["to_status"] for h in body["history"]] == ["open"]


def test_report_then_close_lifecycle(client):
    eid = _id(_raise(client))
    rep = client.post(
        f"{ESC}/{eid}/report", json={"ncmec_reference": "CT-2026-000123"}, headers={"X-ORCA-User": "admin"}
    )
    assert rep.status_code == 200, rep.text
    assert rep.json()["status"] == "reported"
    assert rep.json()["ncmec_reference"] == "CT-2026-000123"
    assert rep.json()["reported_by"] == "admin"
    closed = client.post(
        f"{ESC}/{eid}/close", json={"reason": "Filed; nothing further."}, headers={"X-ORCA-User": "admin"}
    )
    assert closed.json()["status"] == "closed"
    assert [h["to_status"] for h in closed.json()["history"]] == ["open", "reported", "closed"]


def test_cannot_close_before_reporting(client):
    eid = _id(_raise(client))
    resp = client.post(f"{ESC}/{eid}/close", json={"reason": "x"}, headers={"X-ORCA-User": "admin"})
    assert resp.status_code == 422


def test_dismiss_open_escalation(client):
    eid = _id(_raise(client))
    resp = client.post(
        f"{ESC}/{eid}/dismiss", json={"reason": "Adult; not CSAM."}, headers={"X-ORCA-User": "admin"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "dismissed"


def test_listing_and_decisions_are_admin_only(client):
    eid = _id(_raise(client))
    for user in ("ana", "rae", "vic", "partner"):
        assert client.get(ESC, headers={"X-ORCA-User": user}).status_code == 403
        report = client.post(
            f"{ESC}/{eid}/report", json={"ncmec_reference": "x"}, headers={"X-ORCA-User": user}
        )
        assert report.status_code == 403
    # Admin can list.
    assert client.get(ESC, headers={"X-ORCA-User": "admin"}).status_code == 200
