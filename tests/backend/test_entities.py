"""Entity endpoints, including deduplication by (entity_type, value)."""

from __future__ import annotations

PREFIX = "/api/v1"


def test_list_entities_returns_seed(client):
    resp = client.get(f"{PREFIX}/entities")
    assert resp.status_code == 200
    assert len(resp.json()) >= 4


def test_create_entity(client):
    resp = client.post(
        f"{PREFIX}/entities",
        json={"entity_type": "username", "value": "newuser_01", "confidence": 0.5},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["entity_type"] == "username"
    assert body["value"] == "newuser_01"


def test_entity_is_deduplicated(client):
    payload = {"entity_type": "phone_number", "value": "+15555550199"}
    first = client.post(f"{PREFIX}/entities", json=payload).json()
    second = client.post(f"{PREFIX}/entities", json=payload).json()
    # Same (type, value) resolves to the same entity rather than creating a duplicate.
    assert first["id"] == second["id"]


def test_confidence_must_be_in_range(client):
    resp = client.post(
        f"{PREFIX}/entities",
        json={"entity_type": "alias", "value": "x", "confidence": 1.5},
    )
    assert resp.status_code == 422
