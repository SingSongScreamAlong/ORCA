"""Case Membership & Authorization Scoping (v0.6).

Proves the need-to-know guarantees:

* case listing is scoped — admins see all, members see only assigned, unassigned see none
* an unassigned user is forbidden from opening / mutating / graphing / auditing a case
* a 403 is generic and reveals neither the case's contents nor whether it exists
* mutation, review, and report access are gated by the *case* role, not just the global one
* the review queue shows only items from cases the caller may review
* a partner export viewer reaches approved reports only for assigned cases, never raw material
* membership add / role-change / deactivate / reactivate work and are audited
* only an administrator or the case's manager may manage the roster
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

PREFIX = "/api/v1"
FORBIDDEN = "You do not have access to this case."


def H(user: str) -> dict:
    return {"X-ORCA-User": user}


def _seed_case(client) -> str:
    return client.get(f"{PREFIX}/cases", headers=H("admin")).json()[0]["id"]


def _source(client) -> str:
    return client.get(f"{PREFIX}/sources", headers=H("admin")).json()[0]["id"]


def _new_case(client, actor="admin", title="Fresh") -> str:
    return client.post(
        f"{PREFIX}/cases", json={"title": title, "owner": actor}, headers=H(actor)
    ).json()["id"]


def _intake(client, user: str, case_id: str, src: str, note="obs") -> str:
    e = client.post(
        f"{PREFIX}/entities",
        json={"entity_type": "username", "value": f"{user}-{note}-{uuid.uuid4().hex[:6]}"},
        headers=H(user),
    ).json()["id"]
    return client.post(
        f"{PREFIX}/observations",
        json={
            "case_id": case_id, "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_id": src, "collector": user, "notes": note, "confidence": 0.6,
            "entity_ids": [e],
        },
        headers=H(user),
    ).json()


def _assign(client, case_id, username, case_role, actor="admin"):
    return client.post(
        f"{PREFIX}/cases/{case_id}/members",
        json={"username": username, "case_role": case_role},
        headers=H(actor),
    )


# --- listing scope --------------------------------------------------------------


def test_case_list_is_scoped_to_membership(client):
    seed = _seed_case(client)  # capture before any new cases are created
    other = _new_case(client, "admin", "Admin-only")  # admin is the only member
    # Admin sees every case.
    admin_ids = {c["id"] for c in client.get(f"{PREFIX}/cases", headers=H("admin")).json()}
    assert other in admin_ids and len(admin_ids) >= 2
    # A member sees the seed case but not the admin-only one.
    vic_ids = {c["id"] for c in client.get(f"{PREFIX}/cases", headers=H("vic")).json()}
    assert seed in vic_ids
    assert other not in vic_ids
    # The unassigned user sees nothing — a calm empty list, not an error.
    nomad = client.get(f"{PREFIX}/cases", headers=H("nomad"))
    assert nomad.status_code == 200
    assert nomad.json() == []


# --- the unassigned user is walled off ------------------------------------------


def test_unassigned_user_is_forbidden_everywhere(client):
    seed = _seed_case(client)
    for path in (
        f"/cases/{seed}", f"/cases/{seed}/observations", f"/cases/{seed}/relationships",
        f"/cases/{seed}/evidence", f"/cases/{seed}/timeline", f"/cases/{seed}/graph",
        f"/cases/{seed}/reports",
    ):
        r = client.get(f"{PREFIX}{path}", headers=H("nomad"))
        assert r.status_code == 403, path
        # Generic message — no title, summary, or counts leak through.
        assert r.json()["detail"] == FORBIDDEN
        assert "Shared-phone" not in r.text


def test_forbidden_does_not_reveal_case_existence(client):
    # A non-member gets the SAME 403 for a real and a non-existent case, so the response
    # cannot be used to enumerate which cases exist.
    real = client.get(f"{PREFIX}/cases/{_seed_case(client)}", headers=H("nomad"))
    ghost = client.get(f"{PREFIX}/cases/{uuid.uuid4()}", headers=H("nomad"))
    assert real.status_code == ghost.status_code == 403
    assert real.json() == ghost.json()


def test_unassigned_user_cannot_mutate_a_case(client):
    seed = _seed_case(client)
    src = _source(client)
    # nomad is a global analyst (can create entities) but is not on this case.
    e = client.post(
        f"{PREFIX}/entities", json={"entity_type": "alias", "value": "nomad-x"}, headers=H("nomad")
    )
    assert e.status_code == 201
    r = client.post(
        f"{PREFIX}/observations",
        json={
            "case_id": seed, "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_id": src, "collector": "nomad", "notes": "n", "confidence": 0.5,
            "entity_ids": [e.json()["id"]],
        },
        headers=H("nomad"),
    )
    assert r.status_code == 403
    assert r.json()["detail"] == FORBIDDEN


# --- mutation is gated by the CASE role -----------------------------------------


def test_viewer_member_cannot_mutate_but_analyst_member_can(client):
    case_id = _new_case(client, "admin", "Roles")
    src = _source(client)
    _assign(client, case_id, "ana", "analyst")
    _assign(client, case_id, "vic", "viewer")
    # The analyst member may record an observation.
    assert _intake(client, "ana", case_id, src)["status"] == "proposed"
    # The viewer member may read but not create (no global create capability either).
    assert client.get(f"{PREFIX}/cases/{case_id}", headers=H("vic")).status_code == 200
    blocked = client.post(
        f"{PREFIX}/observations",
        json={
            "case_id": case_id, "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_id": src, "collector": "vic", "notes": "n", "confidence": 0.5, "entity_ids": [],
        },
        headers=H("vic"),
    )
    assert blocked.status_code == 403


# --- review is gated by the CASE role -------------------------------------------


def test_reviewer_can_only_review_assigned_cases(client):
    # A fresh case where rae is NOT a reviewer.
    case_id = _new_case(client, "admin", "Unreviewed")
    src = _source(client)
    obs = _intake(client, "admin", case_id, src)
    item = next(
        i for i in client.get(f"{PREFIX}/review", headers=H("admin")).json()
        if i["subject_id"] == obs["id"]
    )
    # rae has global review authority but no reviewer membership here → 403.
    denied = client.post(
        f"{PREFIX}/review/{item['id']}/decision", json={"decision": "approve"}, headers=H("rae")
    )
    assert denied.status_code == 403
    assert denied.json()["detail"] == FORBIDDEN
    # The item never appears in rae's queue.
    assert all(i["case_id"] != case_id for i in client.get(f"{PREFIX}/review", headers=H("rae")).json())


def test_review_queue_is_scoped_to_reviewer_cases(client):
    seed = _seed_case(client)
    # rae reviews the seed case; every queued item rae sees belongs to a case rae reviews.
    rae_queue = client.get(f"{PREFIX}/review", headers=H("rae")).json()
    assert rae_queue, "the seed case has a pending review item"
    assert all(i["case_id"] == seed for i in rae_queue)
    # The unassigned user's queue is empty.
    assert client.get(f"{PREFIX}/review", headers=H("nomad")).json() == []


# --- partner export viewer ------------------------------------------------------


def test_partner_sees_approved_report_only_for_assigned_case(client):
    seed = _seed_case(client)  # partner is a member of the seed case
    report = client.post(f"{PREFIX}/cases/{seed}/report", headers=H("ana")).json()
    client.post(f"{PREFIX}/reports/{report['id']}/publish", headers=H("casey"))
    # Partner can reach the published package for their assigned case.
    assert client.get(f"{PREFIX}/reports/{report['id']}", headers=H("partner")).status_code == 200
    assert any(
        r["id"] == report["id"]
        for r in client.get(f"{PREFIX}/reports/published", headers=H("partner")).json()
    )
    # But never the raw material behind it.
    assert client.get(f"{PREFIX}/cases/{seed}/evidence", headers=H("partner")).status_code == 403
    assert client.get(f"{PREFIX}/cases/{seed}/graph", headers=H("partner")).status_code == 403


def test_partner_cannot_see_report_for_unassigned_case(client):
    other = _new_case(client, "admin", "No-partner")
    report = client.post(f"{PREFIX}/cases/{other}/report", headers=H("admin")).json()
    client.post(f"{PREFIX}/reports/{report['id']}/publish", headers=H("admin"))
    # The report is final, but the partner is not a member of this case.
    assert client.get(f"{PREFIX}/reports/{report['id']}", headers=H("partner")).status_code == 403
    assert all(
        r["id"] != report["id"]
        for r in client.get(f"{PREFIX}/reports/published", headers=H("partner")).json()
    )


# --- graph scoping --------------------------------------------------------------


def test_graph_is_scoped_to_accessible_cases(client):
    seed = _seed_case(client)
    # A member sees the seed subgraph; an unassigned user is refused outright.
    assert client.get(f"{PREFIX}/cases/{seed}/graph", headers=H("vic")).status_code == 200
    assert client.get(f"{PREFIX}/cases/{seed}/graph", headers=H("nomad")).status_code == 403
    # The seed has an approved shared_phone edge; a neighbours query by a member finds it,
    # while the unassigned user traverses nothing.
    edge = client.get(f"{PREFIX}/cases/{seed}/graph", headers=H("admin")).json()["edges"][0]
    node = edge["source_entity_id"]
    member_view = client.get(f"{PREFIX}/graph/neighbors/{node}", headers=H("vic")).json()
    assert member_view["edges"]
    nomad_view = client.get(f"{PREFIX}/graph/neighbors/{node}", headers=H("nomad")).json()
    assert nomad_view["edges"] == []


# --- membership management + audit ----------------------------------------------


def test_only_admin_or_case_manager_manages_members(client):
    seed = _seed_case(client)
    # An analyst or viewer member cannot manage the roster.
    assert _assign(client, seed, "nomad", "viewer", actor="ana").status_code == 403
    assert _assign(client, seed, "nomad", "viewer", actor="vic").status_code == 403
    # The seed's case manager (casey) and the admin can.
    assert _assign(client, seed, "nomad", "viewer", actor="casey").status_code in (201, 422)


def test_membership_lifecycle_is_audited(client):
    case_id = _new_case(client, "casey", "Lifecycle")  # casey is creator/manager
    member = _assign(client, case_id, "vic", "viewer", actor="casey").json()
    assert member["case_role"] == "viewer" and member["status"] == "active"

    changed = client.patch(
        f"{PREFIX}/cases/{case_id}/members/{member['id']}",
        json={"case_role": "analyst"}, headers=H("casey"),
    ).json()
    assert changed["case_role"] == "analyst"

    removed = client.delete(
        f"{PREFIX}/cases/{case_id}/members/{member['id']}", headers=H("casey")
    ).json()
    assert removed["status"] == "revoked"

    actions = [e["action"] for e in client.get(f"{PREFIX}/cases/{case_id}/audit", headers=H("casey")).json()]
    assert "case.member_added" in actions
    assert "case.member_role_changed" in actions
    assert "case.member_deactivated" in actions


def test_deactivated_member_loses_access_and_can_be_reactivated(client):
    case_id = _new_case(client, "admin", "Revoke")
    member = _assign(client, case_id, "vic", "viewer").json()
    assert client.get(f"{PREFIX}/cases/{case_id}", headers=H("vic")).status_code == 200

    client.delete(f"{PREFIX}/cases/{case_id}/members/{member['id']}", headers=H("admin"))
    assert client.get(f"{PREFIX}/cases/{case_id}", headers=H("vic")).status_code == 403

    # Re-adding reuses the one membership row rather than creating a duplicate.
    reactivated = _assign(client, case_id, "vic", "reviewer").json()
    assert reactivated["status"] == "active"
    assert reactivated["case_role"] == "reviewer"
    roster = client.get(f"{PREFIX}/cases/{case_id}/members", headers=H("admin")).json()
    assert sum(1 for m in roster if m["username"] == "vic") == 1
    assert client.get(f"{PREFIX}/cases/{case_id}", headers=H("vic")).status_code == 200


def test_case_creator_becomes_manager(client):
    case_id = _new_case(client, "casey", "Casey's case")
    # casey can immediately open and manage the case they created.
    assert client.get(f"{PREFIX}/cases/{case_id}", headers=H("casey")).status_code == 200
    roster = client.get(f"{PREFIX}/cases/{case_id}/members", headers=H("casey")).json()
    casey_member = next(m for m in roster if m["username"] == "casey")
    assert casey_member["case_role"] == "case_manager"
    assert case_id in {c["id"] for c in client.get(f"{PREFIX}/cases", headers=H("casey")).json()}


def test_member_read_exposes_case_role_and_status(client):
    seed = _seed_case(client)
    roster = client.get(f"{PREFIX}/cases/{seed}/members", headers=H("admin")).json()
    rae = next(m for m in roster if m["username"] == "rae")
    assert rae["case_role"] == "reviewer"
    assert rae["global_role"] == "reviewer"
    assert rae["status"] == "active"
    assert rae["assigned_by"] == "admin"
