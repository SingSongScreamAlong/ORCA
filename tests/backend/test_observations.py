"""Observation endpoints and invariants."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

PREFIX = "/api/v1"


def _a_source_id(client) -> str:
    return client.get(f"{PREFIX}/sources").json()[0]["id"]


def test_list_observations_returns_seed(client):
    resp = client.get(f"{PREFIX}/observations")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_create_observation_requires_existing_source(client):
    resp = client.post(
        f"{PREFIX}/observations",
        json={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_id": str(uuid.uuid4()),  # does not exist
            "collector": "tester",
            "confidence": 0.5,
        },
    )
    # Ontology invariant: an observation must reference an existing source.
    assert resp.status_code == 422


def test_create_observation_succeeds(client):
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
    assert body["collector"] == "tester"

    # It is now retrievable and the count grew.
    assert client.get(f"{PREFIX}/observations/{body['id']}").status_code == 200
    assert len(client.get(f"{PREFIX}/observations").json()) == 3
