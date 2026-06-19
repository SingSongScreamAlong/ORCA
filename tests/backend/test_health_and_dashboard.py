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
    # What is new / what requires review.
    assert body["counts"]["observations"] == 2
    assert body["counts"]["relationships"] == 1
    assert body["counts"]["pending_review"] == 1
    assert len(body["review_queue"]) == 1
    assert body["system_health"]["status"] == "ok"
