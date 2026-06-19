"""Observation intake endpoint and its invariants."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

PREFIX = "/api/v1"


def _a_source_id(client) -> str:
    return client.get(f"{PREFIX}/sources").json()[0]["id"]


def test_list_observations_returns_seed(client):
    resp = client.get(f"{PREFIX}/observations")
    assert resp.status_code == 200
    # v0.2 seed: two approved + one proposed.
    assert len(resp.json()) == 3


def test_filter_observations_by_status(client):
    approved = client.get(f"{PREFIX}/observations", params={"status": "approved"}).json()
    proposed = client.get(f"{PREFIX}/observations", params={"status": "proposed"}).json()
    assert len(approved) == 2
    assert len(proposed) == 1


def test_intake_requires_a_source(client):
    resp = client.post(
        f"{PREFIX}/observations",
        json={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "collector": "tester",
            "confidence": 0.5,
        },
    )
    # Schema requires exactly one of source_id / source.
    assert resp.status_code == 422


def test_intake_rejects_unknown_source(client):
    resp = client.post(
        f"{PREFIX}/observations",
        json={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_id": str(uuid.uuid4()),
            "collector": "tester",
        },
    )
    assert resp.status_code == 422


def test_intake_with_existing_source_starts_proposed(client):
    source_id = _a_source_id(client)
    resp = client.post(
        f"{PREFIX}/observations",
        json={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_id": source_id,
            "collector": "tester",
            "notes": "A new observation.",
            "confidence": 0.7,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source_id"] == source_id
    assert body["status"] == "proposed"
    assert client.get(f"{PREFIX}/observations/{body['id']}").status_code == 200
    assert len(client.get(f"{PREFIX}/observations").json()) == 4


def test_intake_with_inline_source_creates_source(client):
    before = len(client.get(f"{PREFIX}/sources").json())
    resp = client.post(
        f"{PREFIX}/observations",
        json={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": {"source_type": "tip", "name": "Anonymous tip", "reliability": "low"},
            "collector": "tester",
            "handling": {"lawful_basis": "received tip", "requires_legal_review": True},
        },
    )
    assert resp.status_code == 201
    assert len(client.get(f"{PREFIX}/sources").json()) == before + 1
    # Handling metadata round-trips.
    assert resp.json()["handling"]["requires_legal_review"] is True
