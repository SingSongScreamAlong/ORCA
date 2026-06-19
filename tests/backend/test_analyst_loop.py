"""The v0.2 analyst loop, end to end, and the invariants that protect it.

These tests prove the four guarantees the milestone requires:

1. rejected observations do not affect relationships
2. relationships cannot exist without supporting approved observations
3. every status change writes an audit event
4. report drafts exclude proposed/rejected observations
"""

from __future__ import annotations

from datetime import datetime, timezone

PREFIX = "/api/v1"


def _make_case(client, title="Case") -> str:
    # Created by the default admin; assign the reviewer so they may decide in this case
    # (v0.6 per-case authorization). Intake/relationships here are done by the admin.
    case_id = client.post(
        f"{PREFIX}/cases", json={"title": title, "owner": "analyst", "summary": "s"}
    ).json()["id"]
    client.post(
        f"{PREFIX}/cases/{case_id}/members", json={"username": "rae", "case_role": "reviewer"}
    )
    return case_id


def _entity(client, entity_type: str, value: str) -> str:
    return client.post(
        f"{PREFIX}/entities", json={"entity_type": entity_type, "value": value}
    ).json()["id"]


def _intake(client, case_id: str, entity_ids: list[str], notes="obs") -> dict:
    return client.post(
        f"{PREFIX}/observations",
        json={
            "case_id": case_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": {"source_type": "website", "name": "Site", "reliability": "medium"},
            "collector": "analyst",
            "notes": notes,
            "confidence": 0.7,
            "entity_ids": entity_ids,
            "handling": {"lawful_basis": "publicly available information"},
        },
    ).json()


def _review_item_for(client, observation_id: str) -> str:
    items = client.get(f"{PREFIX}/review", params={"status": "proposed"}).json()
    return next(i["id"] for i in items if i["subject_id"] == observation_id)


# Decisions are made by a reviewer (separation of duties); the proposer is the default
# admin user, so a reviewer approving is not self-review.
REVIEWER = {"X-ORCA-User": "rae"}


def _decide(client, item_id: str, decision: str):
    return client.post(
        f"{PREFIX}/review/{item_id}/decision", json={"decision": decision}, headers=REVIEWER
    )


# --- the happy-path loop --------------------------------------------------------


def test_full_loop_intake_to_report(client):
    case_id = _make_case(client, "Full loop")
    a = _entity(client, "phone_number", "+15555551234")
    b = _entity(client, "advertisement", "ad-loop")

    observation = _intake(client, case_id, [a, b], notes="phone in ad-loop")
    assert observation["status"] == "proposed"
    assert observation["case_id"] == case_id

    # It is awaiting review.
    item_id = _review_item_for(client, observation["id"])
    assert _decide(client, item_id, "approve").json()["status"] == "approved"
    assert client.get(f"{PREFIX}/observations/{observation['id']}").json()["status"] == "approved"

    # Relationship from the approved observation.
    rel = client.post(
        f"{PREFIX}/relationships",
        json={
            "case_id": case_id,
            "source_entity_id": a,
            "target_entity_id": b,
            "relationship_type": "shared_phone",
            "observation_ids": [observation["id"]],
            "confidence": 0.6,
        },
    )
    assert rel.status_code == 201
    assert rel.json()["status"] == "approved"

    # Timeline shows the approved observation and the relationship.
    timeline = client.get(f"{PREFIX}/cases/{case_id}/timeline").json()
    kinds = {e["kind"] for e in timeline}
    assert "observation_approved" in kinds
    assert {"relationship_approved", "relationship_created"} & kinds

    # Report draft generated.
    report = client.post(f"{PREFIX}/cases/{case_id}/report")
    assert report.status_code == 201
    assert report.json()["status"] == "draft"


# --- invariant 2: relationships need approved supporting observations -----------


def test_relationship_requires_supporting_observation(client):
    case_id = _make_case(client)
    a = _entity(client, "phone_number", "+15555550001")
    b = _entity(client, "advertisement", "ad-1")
    resp = client.post(
        f"{PREFIX}/relationships",
        json={
            "case_id": case_id,
            "source_entity_id": a,
            "target_entity_id": b,
            "relationship_type": "shared_phone",
            "observation_ids": [],  # invalid
        },
    )
    assert resp.status_code == 422


def test_relationship_rejected_when_observation_only_proposed(client):
    case_id = _make_case(client)
    a = _entity(client, "phone_number", "+15555550002")
    b = _entity(client, "advertisement", "ad-2")
    obs = _intake(client, case_id, [a, b])  # stays proposed
    resp = client.post(
        f"{PREFIX}/relationships",
        json={
            "source_entity_id": a,
            "target_entity_id": b,
            "relationship_type": "shared_phone",
            "observation_ids": [obs["id"]],
        },
    )
    assert resp.status_code == 422
    assert "approved" in resp.json()["detail"].lower()


# --- invariant 1: rejected observations do not affect relationships -------------


def test_rejected_observation_cannot_support_a_relationship(client):
    case_id = _make_case(client)
    a = _entity(client, "phone_number", "+15555550003")
    b = _entity(client, "advertisement", "ad-3")
    obs = _intake(client, case_id, [a, b])
    item_id = _review_item_for(client, obs["id"])
    assert _decide(client, item_id, "reject").json()["status"] == "rejected"
    assert client.get(f"{PREFIX}/observations/{obs['id']}").json()["status"] == "rejected"

    resp = client.post(
        f"{PREFIX}/relationships",
        json={
            "source_entity_id": a,
            "target_entity_id": b,
            "relationship_type": "shared_phone",
            "observation_ids": [obs["id"]],
        },
    )
    assert resp.status_code == 422
    # No relationship was created from the rejected evidence.
    rels = client.get(f"{PREFIX}/relationships", params={"case_id": case_id}).json()
    assert rels == []


# --- invariant 3: every status change writes an audit event ---------------------


def test_every_status_change_is_audited(client):
    case_id = _make_case(client, "Audited")
    a = _entity(client, "phone_number", "+15555550004")
    b = _entity(client, "advertisement", "ad-4")
    obs = _intake(client, case_id, [a, b])
    item_id = _review_item_for(client, obs["id"])
    _decide(client, item_id, "approve")
    client.post(
        f"{PREFIX}/relationships",
        json={
            "source_entity_id": a,
            "target_entity_id": b,
            "relationship_type": "shared_phone",
            "observation_ids": [obs["id"]],
        },
    )

    actions = [e["action"] for e in client.get(f"{PREFIX}/cases/{case_id}/audit").json()]
    assert "case.created" in actions
    assert "observation.intake" in actions
    assert "review.approve" in actions
    assert "relationship.created" in actions


def test_reject_is_audited(client):
    case_id = _make_case(client)
    a = _entity(client, "phone_number", "+15555550005")
    b = _entity(client, "advertisement", "ad-5")
    obs = _intake(client, case_id, [a, b])
    item_id = _review_item_for(client, obs["id"])
    _decide(client, item_id, "reject")
    actions = [e["action"] for e in client.get(f"{PREFIX}/cases/{case_id}/audit").json()]
    assert "review.reject" in actions


# --- invariant 4: report draft excludes proposed/rejected observations ----------


def test_report_draft_excludes_non_approved_observations(client):
    case_id = _make_case(client, "Reporting")
    a = _entity(client, "phone_number", "+15555550006")
    b = _entity(client, "advertisement", "ad-approved")
    cc = _entity(client, "username", "user-pending")
    d = _entity(client, "username", "user-rejected")

    approved = _intake(client, case_id, [a, b], notes="APPROVED-NOTE in ad-approved")
    pending = _intake(client, case_id, [a, cc], notes="PENDING-NOTE user-pending")
    rejected = _intake(client, case_id, [a, d], notes="REJECTED-NOTE user-rejected")

    _decide(client, _review_item_for(client, approved["id"]), "approve")
    _decide(client, _review_item_for(client, rejected["id"]), "reject")
    # 'pending' is left proposed.

    body = client.post(f"{PREFIX}/cases/{case_id}/report").json()["body"]
    assert "APPROVED-NOTE" in body
    assert "PENDING-NOTE" not in body
    assert "REJECTED-NOTE" not in body


# --- needs_more_review defers without confirming --------------------------------


def test_needs_more_review_defers(client):
    case_id = _make_case(client)
    a = _entity(client, "phone_number", "+15555550007")
    b = _entity(client, "advertisement", "ad-7")
    obs = _intake(client, case_id, [a, b])
    item_id = _review_item_for(client, obs["id"])
    assert _decide(client, item_id, "needs_more_review").json()["status"] == "needs_more_review"
    assert client.get(f"{PREFIX}/observations/{obs['id']}").json()["status"] == "needs_more_review"
    # Still not usable for a relationship.
    resp = client.post(
        f"{PREFIX}/relationships",
        json={
            "source_entity_id": a,
            "target_entity_id": b,
            "relationship_type": "shared_phone",
            "observation_ids": [obs["id"]],
        },
    )
    assert resp.status_code == 422
