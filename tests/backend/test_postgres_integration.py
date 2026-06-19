"""PostgreSQL integration test for the analyst loop.

Runs the full intake -> review -> relationship -> report loop against a real
PostgreSQL database through the SQL unit of work, proving the persistence path.

Skipped unless ``ORCA_RUN_PG_IT=1`` and a reachable ``ORCA_POSTGRES_DSN`` are set, and
the schema has been created (``alembic upgrade head``). See docs/roadmap / README.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("ORCA_RUN_PG_IT") != "1",
    reason="set ORCA_RUN_PG_IT=1 (and a migrated ORCA_POSTGRES_DSN) to run the PG integration test",
)

PREFIX = "/api/v1"
REVIEWER = {"X-ORCA-User": "rae"}  # decisions by a reviewer (proposer is the default admin)


@pytest.fixture
def pg_client():
    """A TestClient bound to the PostgreSQL backend for the duration of the test."""
    from fastapi.testclient import TestClient

    from app.core.config import get_settings

    prev_backend = os.environ.get("ORCA_STORAGE_BACKEND")
    os.environ["ORCA_STORAGE_BACKEND"] = "postgres"
    get_settings.cache_clear()
    from app.db.seed import seed_demo_users
    from app.main import app
    from app.repositories.uow import build_unit_of_work

    # Authentication needs identities to resolve; seed demo users into the DB.
    uow = build_unit_of_work()
    seed_demo_users(uow)
    uow.commit()
    uow.close()

    try:
        yield TestClient(app)
    finally:
        if prev_backend is None:
            os.environ.pop("ORCA_STORAGE_BACKEND", None)
        else:
            os.environ["ORCA_STORAGE_BACKEND"] = prev_backend
        get_settings.cache_clear()


def test_full_loop_against_postgres(pg_client):
    c = pg_client
    assert c.get(f"{PREFIX}/health").json()["storage_backend"] == "postgres"

    case = c.post(f"{PREFIX}/cases", json={"title": "PG loop", "owner": "analyst"}).json()
    cid = case["id"]
    # Assign the reviewer so they may decide in this case (v0.6 per-case authorization).
    c.post(f"{PREFIX}/cases/{cid}/members", json={"username": "rae", "case_role": "reviewer"})

    a = c.post(f"{PREFIX}/entities", json={"entity_type": "phone_number", "value": "+15555559000"}).json()["id"]
    b = c.post(f"{PREFIX}/entities", json={"entity_type": "advertisement", "value": "ad-pg"}).json()["id"]

    obs = c.post(
        f"{PREFIX}/observations",
        json={
            "case_id": cid,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": {"source_type": "website", "name": "Site", "reliability": "medium"},
            "collector": "analyst",
            "notes": "PG-LOOP phone in ad-pg",
            "confidence": 0.7,
            "entity_ids": [a, b],
            "handling": {"lawful_basis": "publicly available information"},
        },
    ).json()
    assert obs["status"] == "proposed"

    # Relationship blocked while observation is only proposed.
    blocked = c.post(
        f"{PREFIX}/relationships",
        json={
            "source_entity_id": a, "target_entity_id": b,
            "relationship_type": "shared_phone", "observation_ids": [obs["id"]],
        },
    )
    assert blocked.status_code == 422

    # Approve via the review queue.
    items = c.get(f"{PREFIX}/review", params={"case_id": cid, "status": "proposed"}).json()
    item_id = next(i["id"] for i in items if i["subject_id"] == obs["id"])
    decided = c.post(
        f"{PREFIX}/review/{item_id}/decision", json={"decision": "approve"}, headers=REVIEWER
    )
    assert decided.json()["status"] == "approved"

    # Now the relationship persists.
    rel = c.post(
        f"{PREFIX}/relationships",
        json={
            "case_id": cid, "source_entity_id": a, "target_entity_id": b,
            "relationship_type": "shared_phone", "observation_ids": [obs["id"]], "confidence": 0.6,
        },
    )
    assert rel.status_code == 201

    # Evidence locker: create (hashed), link, verify, approve — all persisted.
    ev = c.post(
        f"{PREFIX}/evidence",
        json={
            "case_id": cid, "source_id": obs["source_id"], "title": "PG-EVIDENCE",
            "evidence_type": "analyst_note", "content_text": "pg evidence bytes",
        },
    ).json()
    assert ev["sha256"] and ev["has_bytes"] is True
    assert c.post(f"{PREFIX}/evidence/{ev['id']}/link", json={"observation_id": obs["id"]}).status_code == 200
    assert c.post(f"{PREFIX}/evidence/{ev['id']}/verify").json()["verified"] is True
    c.post(f"{PREFIX}/evidence/{ev['id']}/decision", json={"decision": "approve"}, headers=REVIEWER)
    assert any(e["title"] == "PG-EVIDENCE" for e in c.get(f"{PREFIX}/cases/{cid}/evidence").json())

    # Manual file upload (v0.7): multipart upload → filesystem content store → download +
    # verify, exercising the SQL + content-store path end to end.
    import hashlib

    blob = b"pg upload bytes"
    up = c.post(
        f"{PREFIX}/cases/{cid}/evidence/upload",
        files={"file": ("pg.txt", blob, "text/plain")},
        data={"source_id": obs["source_id"], "title": "PG-UPLOAD", "acknowledged": "true"},
    ).json()
    assert up["sha256"] == hashlib.sha256(blob).hexdigest()
    assert up["has_bytes"] is True
    dl = c.get(f"{PREFIX}/evidence/{up['id']}/download")
    assert dl.status_code == 200 and dl.content == blob
    assert c.post(f"{PREFIX}/evidence/{up['id']}/verify").json()["verified"] is True

    # Timeline, report, and audit all reflect the persisted state.
    timeline = c.get(f"{PREFIX}/cases/{cid}/timeline").json()
    assert any(e["kind"] == "observation_approved" for e in timeline)

    report = c.post(f"{PREFIX}/cases/{cid}/report").json()
    assert "PG-LOOP" in report["body"]
    assert "PG-EVIDENCE" in report["body"]  # approved evidence cited

    actions = [e["action"] for e in c.get(f"{PREFIX}/cases/{cid}/audit").json()]
    for expected in (
        "case.created", "observation.intake", "review.approve", "relationship.created",
        "evidence.created", "evidence.linked", "evidence.verified", "evidence.approve",
        "evidence.uploaded", "evidence.downloaded",
    ):
        assert expected in actions
