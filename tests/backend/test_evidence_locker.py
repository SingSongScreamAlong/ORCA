"""Evidence Locker + Integrity Layer (v0.3).

Proves the required guarantees:

* evidence creation writes an audit event
* SHA-256 is deterministic and verified
* rejected / quarantined evidence is excluded from reports
* report drafts cite only approved observations + approved evidence
* evidence cannot be linked across unrelated cases
* every evidence status change writes an audit event
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

PREFIX = "/api/v1"

# Decisions are made by a reviewer (separation of duties); evidence/observations are
# created by the default admin user, so a reviewer deciding is not self-review.
REVIEWER = {"X-ORCA-User": "rae"}


def _case(client, title="Case"):
    # Created by the default admin; assign the reviewer so they may decide evidence in
    # this case (v0.6 per-case authorization).
    case_id = client.post(
        f"{PREFIX}/cases", json={"title": title, "owner": "analyst"}
    ).json()["id"]
    client.post(
        f"{PREFIX}/cases/{case_id}/members", json={"username": "rae", "case_role": "reviewer"}
    )
    return case_id


def _source(client):
    return client.get(f"{PREFIX}/sources").json()[0]["id"]


def _approved_observation(client, case_id, source_id, note="obs"):
    e = client.post(f"{PREFIX}/entities", json={"entity_type": "username", "value": note + "-u"}).json()["id"]
    obs = client.post(
        f"{PREFIX}/observations",
        json={
            "case_id": case_id, "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_id": source_id, "collector": "analyst", "notes": note, "confidence": 0.7,
            "entity_ids": [e],
        },
    ).json()
    item = next(i for i in client.get(f"{PREFIX}/review").json() if i["subject_id"] == obs["id"])
    client.post(f"{PREFIX}/review/{item['id']}/decision", json={"decision": "approve"}, headers=REVIEWER)
    return obs["id"]


def _evidence(client, case_id, source_id, **kw):
    body = {
        "case_id": case_id, "source_id": source_id, "title": kw.pop("title", "Item"),
        "evidence_type": kw.pop("evidence_type", "document"),
    }
    body.update(kw)
    return client.post(f"{PREFIX}/evidence", json=body)


def _actions(client, case_id):
    return [e["action"] for e in client.get(f"{PREFIX}/cases/{case_id}/audit").json()]


# --- creation + audit -----------------------------------------------------------


def test_create_evidence_writes_audit(client):
    case_id = _case(client)
    src = _source(client)
    resp = _evidence(client, case_id, src, title="A note", evidence_type="analyst_note")
    assert resp.status_code == 201
    assert resp.json()["status"] == "proposed"
    assert "evidence.created" in _actions(client, case_id)


def test_evidence_appears_in_case_locker(client):
    case_id = _case(client)
    src = _source(client)
    _evidence(client, case_id, src, title="X")
    locker = client.get(f"{PREFIX}/cases/{case_id}/evidence").json()
    assert any(e["title"] == "X" for e in locker)


# --- SHA-256 deterministic + verified -------------------------------------------


def test_sha256_is_deterministic_and_verified(client):
    case_id = _case(client)
    src = _source(client)
    content = "deterministic evidence content"
    expected = hashlib.sha256(content.encode()).hexdigest()

    a = _evidence(client, case_id, src, title="A", content_text=content).json()
    b = _evidence(client, case_id, src, title="B", content_text=content).json()
    assert a["sha256"] == expected
    assert b["sha256"] == expected  # same bytes -> same hash
    assert a["has_bytes"] is True

    verify = client.post(f"{PREFIX}/evidence/{a['id']}/verify").json()
    assert verify["verified"] is True
    assert verify["computed_sha256"] == expected


def test_verify_without_bytes_is_unknown(client):
    case_id = _case(client)
    src = _source(client)
    # Partner-provided hash, no bytes in ORCA.
    digest = "a" * 64
    ev = _evidence(client, case_id, src, title="Partner", evidence_type="partner_file", sha256=digest).json()
    assert ev["has_bytes"] is False
    verify = client.post(f"{PREFIX}/evidence/{ev['id']}/verify").json()
    assert verify["verified"] is None  # cannot verify without bytes
    assert verify["recorded_sha256"] == digest


# --- linking + cross-case guard -------------------------------------------------


def test_evidence_links_within_case(client):
    case_id = _case(client)
    src = _source(client)
    obs = _approved_observation(client, case_id, src)
    ev = _evidence(client, case_id, src, title="L").json()
    linked = client.post(f"{PREFIX}/evidence/{ev['id']}/link", json={"observation_id": obs})
    assert linked.status_code == 200
    assert linked.json()["observation_id"] == obs
    assert "evidence.linked" in _actions(client, case_id)


def test_evidence_cannot_link_across_cases(client):
    src = _source(client)
    case_a = _case(client, "A")
    case_b = _case(client, "B")
    obs_b = _approved_observation(client, case_b, src)  # observation in a different case
    ev_a = _evidence(client, case_a, src, title="A-ev").json()
    resp = client.post(f"{PREFIX}/evidence/{ev_a['id']}/link", json={"observation_id": obs_b})
    assert resp.status_code == 422
    assert "unrelated cases" in resp.json()["detail"].lower()


# --- decisions are audited ------------------------------------------------------


def test_every_evidence_status_change_is_audited(client):
    case_id = _case(client)
    src = _source(client)
    for decision in ("approve", "reject", "needs_more_review", "quarantine"):
        ev = _evidence(client, case_id, src, title=decision).json()
        resp = client.post(
            f"{PREFIX}/evidence/{ev['id']}/decision", json={"decision": decision}, headers=REVIEWER
        )
        assert resp.status_code == 200
    actions = _actions(client, case_id)
    for decision in ("approve", "reject", "needs_more_review", "quarantine"):
        assert f"evidence.{decision}" in actions


# --- report excludes non-approved evidence --------------------------------------


def test_report_cites_only_approved_evidence(client):
    case_id = _case(client)
    src = _source(client)
    obs = _approved_observation(client, case_id, src, note="primary")

    approved = _evidence(client, case_id, src, title="APPROVED-EV", observation_id=obs, content_text="a").json()
    rejected = _evidence(client, case_id, src, title="REJECTED-EV", observation_id=obs, content_text="b").json()
    quarantined = _evidence(client, case_id, src, title="QUARANTINED-EV", observation_id=obs, content_text="c").json()

    client.post(f"{PREFIX}/evidence/{approved['id']}/decision", json={"decision": "approve"}, headers=REVIEWER)
    client.post(f"{PREFIX}/evidence/{rejected['id']}/decision", json={"decision": "reject"}, headers=REVIEWER)
    client.post(
        f"{PREFIX}/evidence/{quarantined['id']}/decision", json={"decision": "quarantine"}, headers=REVIEWER
    )

    body = client.post(f"{PREFIX}/cases/{case_id}/report").json()["body"]
    assert "APPROVED-EV" in body
    assert "REJECTED-EV" not in body
    assert "QUARANTINED-EV" not in body


def test_report_excludes_evidence_under_unapproved_observation(client):
    case_id = _case(client)
    src = _source(client)
    # An approved evidence item linked to a still-proposed observation must not appear,
    # because the observation itself is not approved.
    e = client.post(f"{PREFIX}/entities", json={"entity_type": "alias", "value": "pend"}).json()["id"]
    obs = client.post(
        f"{PREFIX}/observations",
        json={
            "case_id": case_id, "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_id": src, "collector": "a", "notes": "PENDING-OBS", "confidence": 0.5, "entity_ids": [e],
        },
    ).json()["id"]
    ev = _evidence(client, case_id, src, title="EV-UNDER-PENDING", observation_id=obs, content_text="z").json()
    client.post(f"{PREFIX}/evidence/{ev['id']}/decision", json={"decision": "approve"}, headers=REVIEWER)

    body = client.post(f"{PREFIX}/cases/{case_id}/report").json()["body"]
    assert "EV-UNDER-PENDING" not in body
