"""Auth/RBAC enforcement (v0.4).

Proves the required guarantees:

* analyst can propose but cannot approve
* reviewer can approve another user's proposal
* reviewer cannot approve their own proposal without override
* viewer cannot mutate anything
* partner_export_viewer cannot browse raw evidence (only published reports)
* permission failures return 403 (and unknown users 401)
* privileged actions write audit events
* admin override writes an explicit override audit event
"""

from __future__ import annotations

from datetime import datetime, timezone

PREFIX = "/api/v1"


def H(user: str) -> dict:
    return {"X-ORCA-User": user}


def _source(client) -> str:
    return client.get(f"{PREFIX}/sources", headers=H("admin")).json()[0]["id"]


def _case(client) -> str:
    return client.get(f"{PREFIX}/cases", headers=H("admin")).json()[0]["id"]


def _intake(client, user: str, case_id: str, source_id: str, note="obs") -> str:
    e = client.post(
        f"{PREFIX}/entities", json={"entity_type": "username", "value": f"{user}-{note}"}, headers=H(user)
    ).json()["id"]
    return client.post(
        f"{PREFIX}/observations",
        json={
            "case_id": case_id, "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_id": source_id, "collector": user, "notes": note, "confidence": 0.6,
            "entity_ids": [e],
        },
        headers=H(user),
    ).json()["id"]


def _item_for(client, observation_id: str) -> str:
    items = client.get(f"{PREFIX}/review", headers=H("admin")).json()
    return next(i["id"] for i in items if i["subject_id"] == observation_id)


def _audit_actions(client, case_id: str) -> list[str]:
    return [e["action"] for e in client.get(f"{PREFIX}/cases/{case_id}/audit", headers=H("admin")).json()]


# --- identity -------------------------------------------------------------------


def test_unknown_user_is_401(client):
    assert client.get(f"{PREFIX}/me", headers=H("ghost")).status_code == 401


def test_me_reports_role_and_capabilities(client):
    body = client.get(f"{PREFIX}/me", headers=H("ana")).json()
    assert body["role"] == "analyst"
    assert "create_observation" in body["capabilities"]
    assert "review_decide" not in body["capabilities"]


# --- analyst proposes but cannot approve ----------------------------------------


def test_analyst_can_propose_but_not_approve(client):
    case_id, src = _case(client), _source(client)
    obs = _intake(client, "ana", case_id, src)
    item = _item_for(client, obs)
    resp = client.post(f"{PREFIX}/review/{item}/decision", json={"decision": "approve"}, headers=H("ana"))
    assert resp.status_code == 403


# --- reviewer approval rules ----------------------------------------------------


def test_reviewer_can_approve_another_users_proposal(client):
    case_id, src = _case(client), _source(client)
    obs = _intake(client, "ana", case_id, src)
    item = _item_for(client, obs)
    resp = client.post(f"{PREFIX}/review/{item}/decision", json={"decision": "approve"}, headers=H("rae"))
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_reviewer_cannot_approve_own_proposal_without_override(client):
    case_id, src = _case(client), _source(client)
    obs = _intake(client, "rae", case_id, src)  # reviewer proposes
    item = _item_for(client, obs)
    # Self-review without override → 403.
    assert client.post(
        f"{PREFIX}/review/{item}/decision", json={"decision": "approve"}, headers=H("rae")
    ).status_code == 403
    # Reviewer cannot wield the admin override either.
    assert client.post(
        f"{PREFIX}/review/{item}/decision", json={"decision": "approve", "override": True}, headers=H("rae")
    ).status_code == 403


# --- viewer is read-only --------------------------------------------------------


def test_viewer_cannot_mutate(client):
    case_id, src = _case(client), _source(client)
    # Reads are allowed.
    assert client.get(f"{PREFIX}/cases", headers=H("vic")).status_code == 200
    # Mutations are forbidden.
    assert client.post(f"{PREFIX}/cases", json={"title": "x", "owner": "vic"}, headers=H("vic")).status_code == 403
    assert client.post(
        f"{PREFIX}/entities", json={"entity_type": "alias", "value": "z"}, headers=H("vic")
    ).status_code == 403
    assert client.post(
        f"{PREFIX}/evidence",
        json={"case_id": case_id, "source_id": src, "title": "x", "evidence_type": "document"},
        headers=H("vic"),
    ).status_code == 403


# --- partner export viewer ------------------------------------------------------


def test_partner_cannot_browse_raw_material(client):
    case_id = _case(client)
    for path in ("/cases", "/observations", "/evidence", "/relationships", f"/cases/{case_id}/evidence"):
        assert client.get(f"{PREFIX}{path}", headers=H("partner")).status_code == 403, path


def test_partner_sees_only_published_reports(client):
    case_id = _case(client)
    # Analyst generates a draft; partner cannot see drafts.
    report = client.post(f"{PREFIX}/cases/{case_id}/report", headers=H("ana")).json()
    assert client.get(f"{PREFIX}/reports/{report['id']}", headers=H("partner")).status_code == 403
    # Case manager publishes it; now the partner can access the package.
    published = client.post(f"{PREFIX}/reports/{report['id']}/publish", headers=H("casey"))
    assert published.status_code == 200
    assert published.json()["status"] == "final"
    assert client.get(f"{PREFIX}/reports/{report['id']}", headers=H("partner")).status_code == 200
    listing = client.get(f"{PREFIX}/reports/published", headers=H("partner"))
    assert listing.status_code == 200
    assert any(r["id"] == report["id"] for r in listing.json())


# --- case management ------------------------------------------------------------


def test_case_manager_can_assign_users_but_analyst_cannot(client):
    case_id = _case(client)
    assert client.post(
        f"{PREFIX}/cases/{case_id}/members", json={"username": "vic"}, headers=H("casey")
    ).status_code in (201, 422)  # 422 only if already a member
    assert client.post(
        f"{PREFIX}/cases/{case_id}/members", json={"username": "ana"}, headers=H("ana")
    ).status_code == 403


# --- audit ----------------------------------------------------------------------


def test_privileged_actions_write_audit_events(client):
    src = _source(client)
    case_id = client.post(f"{PREFIX}/cases", json={"title": "Audited", "owner": "casey"}, headers=H("casey")).json()["id"]
    # casey (the creator / case manager) enrols the analyst and reviewer for this case.
    for username, case_role in (("ana", "analyst"), ("rae", "reviewer")):
        client.post(
            f"{PREFIX}/cases/{case_id}/members",
            json={"username": username, "case_role": case_role},
            headers=H("casey"),
        )
    obs = _intake(client, "ana", case_id, src)
    item = _item_for(client, obs)
    client.post(f"{PREFIX}/review/{item}/decision", json={"decision": "approve"}, headers=H("rae"))
    actions = _audit_actions(client, case_id)
    assert "case.created" in actions
    assert "observation.intake" in actions
    assert "review.approve" in actions


def test_admin_override_writes_distinct_override_event(client):
    case_id, src = _case(client), _source(client)
    obs = _intake(client, "admin", case_id, src)  # admin proposes
    item = _item_for(client, obs)
    # Admin must override to approve their own proposal.
    assert client.post(
        f"{PREFIX}/review/{item}/decision", json={"decision": "approve"}, headers=H("admin")
    ).status_code == 403
    ok = client.post(
        f"{PREFIX}/review/{item}/decision", json={"decision": "approve", "override": True}, headers=H("admin")
    )
    assert ok.status_code == 200
    assert "review.override" in _audit_actions(client, case_id)


def test_viewer_cannot_read_audit(client):
    case_id = _case(client)
    assert client.get(f"{PREFIX}/cases/{case_id}/audit", headers=H("vic")).status_code == 403
