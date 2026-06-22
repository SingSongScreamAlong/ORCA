"""Health and dashboard endpoints."""

from __future__ import annotations

PREFIX = "/api/v1"


def test_health_reports_memory_backend(client):
    resp = client.get(f"{PREFIX}/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "ORCA"
    assert body["storage_backend"] == "memory"


def test_dashboard_summary_answers_the_three_questions(client):
    resp = client.get(f"{PREFIX}/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()
    # The v0.2 seed: one case, three observations (two approved + one pending), one
    # relationship, and one pending review item.
    assert body["counts"]["observations"] == 3
    assert body["counts"]["relationships"] == 1
    assert body["counts"]["pending_review"] == 1
    assert body["counts"]["cases"] == 1
    assert len(body["review_queue"]) == 1
    assert body["system_health"]["status"] == "ok"
    # The Hunting Grounds posture is present (empty registry by default).
    assert body["hunting"]["monitored_sources"] == 0
    assert body["hunting"]["cross_venue_links"] == 0


ADMIN = {"X-ORCA-User": "admin"}
ANA = {"X-ORCA-User": "ana"}
AUTH = {
    "lawful_basis": "publicly available; licensed feed",
    "access_method": "licensed search API (read-only)",
    "jurisdiction": "Rhode Island, USA",
}


def test_dashboard_surfaces_hunting_posture(client):
    src = f"{PREFIX}/hunting/sources"

    def monitored(name, url):
        sid = client.post(
            src,
            json={"name": name, "url": url, "category": "escort_listing", "aor": "Rhode Island"},
            headers=ANA,
        ).json()["id"]
        client.post(f"{src}/{sid}/authorize", json=AUTH, headers=ADMIN)
        client.post(f"{src}/{sid}/monitor", headers=ADMIN)
        return sid

    a = monitored("Venue A", "https://a.invalid")
    b = monitored("Venue B", "https://b.invalid")
    client.post(f"{src}/{a}/leads", json={"summary": "call +1 401 555 0142", "confidence": 0.4}, headers=ANA)
    client.post(f"{src}/{b}/leads", json={"summary": "same 401-555-0142", "confidence": 0.4}, headers=ANA)

    h = client.get(f"{PREFIX}/dashboard/summary", headers=ANA).json()["hunting"]
    assert h["monitored_sources"] == 2
    assert h["total_sources"] == 2
    assert h["aors"] == 1
    assert h["leads"] == 2
    assert h["cross_venue_links"] == 1  # the shared phone links both venues
    assert h["top_cross_venue"][0]["value"] == "+14015550142"
