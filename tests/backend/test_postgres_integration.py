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


@pytest.fixture
def pg_client():
    """A TestClient bound to the PostgreSQL backend for the duration of the test."""
    from fastapi.testclient import TestClient

    from app.core.config import get_settings

    prev_backend = os.environ.get("ORCA_STORAGE_BACKEND")
    os.environ["ORCA_STORAGE_BACKEND"] = "postgres"
    get_settings.cache_clear()
    from app.main import app

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
    assert c.post(f"{PREFIX}/review/{item_id}/decision", json={"decision": "approve"}).json()["status"] == "approved"

    # Now the relationship persists.
    rel = c.post(
        f"{PREFIX}/relationships",
        json={
            "case_id": cid, "source_entity_id": a, "target_entity_id": b,
            "relationship_type": "shared_phone", "observation_ids": [obs["id"]], "confidence": 0.6,
        },
    )
    assert rel.status_code == 201

    # Timeline, report, and audit all reflect the persisted state.
    timeline = c.get(f"{PREFIX}/cases/{cid}/timeline").json()
    assert any(e["kind"] == "observation_approved" for e in timeline)

    report = c.post(f"{PREFIX}/cases/{cid}/report").json()
    assert "PG-LOOP" in report["body"]

    actions = [e["action"] for e in c.get(f"{PREFIX}/cases/{cid}/audit").json()]
    for expected in ("case.created", "observation.intake", "review.approve", "relationship.created"):
        assert expected in actions
