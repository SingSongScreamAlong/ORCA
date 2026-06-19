"""The core loop: a system-proposed relationship is reviewed by an analyst, the
decision transitions the relationship, and the action is written to the audit log.

This is the behavioural heart of ORCA — "AI proposes, analysts decide".
"""

from __future__ import annotations

from app.core.audit import audit_log
from app.models.enums import ReviewStatus

PREFIX = "/api/v1"


def _pending_item(client) -> dict:
    items = client.get(f"{PREFIX}/review").json()
    assert items, "expected a seeded pending review item"
    return items[0]


def test_seed_relationship_starts_proposed(client):
    item = _pending_item(client)
    rel = client.get(f"{PREFIX}/relationships/{item['subject_id']}").json()
    assert rel["origin"] == "system_proposed"
    assert rel["status"] == "proposed"
    # The item explains itself and carries supporting evidence.
    assert item["rationale"]
    assert item["evidence_ids"]


def test_approve_confirms_relationship_and_audits(client):
    before = len(audit_log.entries())
    item = _pending_item(client)

    resp = client.post(
        f"{PREFIX}/review/{item['id']}/decision",
        json={"decision": "approve", "note": "verified against both screenshots"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"
    assert resp.json()["decided_by"]  # recorded against an analyst

    # The relationship transitioned to confirmed.
    rel = client.get(f"{PREFIX}/relationships/{item['subject_id']}").json()
    assert rel["status"] == "confirmed"

    # The decision was written to the append-only audit log.
    entries = audit_log.entries()
    assert len(entries) == before + 1
    assert entries[-1].action == "review.approve"
    assert entries[-1].target_id == item["subject_id"]


def test_reject_marks_relationship_rejected(client):
    item = _pending_item(client)
    resp = client.post(f"{PREFIX}/review/{item['id']}/decision", json={"decision": "reject"})
    assert resp.status_code == 200
    rel = client.get(f"{PREFIX}/relationships/{item['subject_id']}").json()
    assert rel["status"] == "rejected"


def test_a_decided_item_cannot_be_decided_again(client):
    item = _pending_item(client)
    client.post(f"{PREFIX}/review/{item['id']}/decision", json={"decision": "approve"})
    second = client.post(f"{PREFIX}/review/{item['id']}/decision", json={"decision": "reject"})
    assert second.status_code == 422


def test_relationship_requires_supporting_observation(client):
    entities = client.get(f"{PREFIX}/entities").json()
    a, b = entities[0]["id"], entities[1]["id"]
    resp = client.post(
        f"{PREFIX}/relationships",
        json={
            "source_entity_id": a,
            "target_entity_id": b,
            "relationship_type": "appears_with",
            "observation_ids": [],  # invalid: at least one is required
        },
    )
    assert resp.status_code == 422


def test_analyst_submitted_relationship_goes_to_review(client):
    entities = client.get(f"{PREFIX}/entities").json()
    observations = client.get(f"{PREFIX}/observations").json()
    a, b = entities[0]["id"], entities[1]["id"]
    resp = client.post(
        f"{PREFIX}/relationships",
        json={
            "source_entity_id": a,
            "target_entity_id": b,
            "relationship_type": "appears_with",
            "confidence": 0.5,
            "observation_ids": [observations[0]["id"]],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["origin"] == "analyst_created"
    assert body["status"] == ReviewStatus.PROPOSED.value
    # A review item was created for it.
    pending = client.get(f"{PREFIX}/review").json()
    assert any(i["subject_id"] == body["id"] for i in pending)
