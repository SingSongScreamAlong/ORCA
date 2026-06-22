"""Hunting Grounds — continuous (scheduled) discovery.

The autonomous cadence inherits every discovery guardrail (proposes only; configured lawful
source; CSAM-safe) and adds two operator controls: a config gate to enable the loop, and a
runtime **kill-switch** (pause/resume). These tests exercise the run path and the controls
without starting a real timer — the loop just calls ``run_once``, which is tested directly.
"""

from __future__ import annotations

from app.services.hunting_scheduler import DiscoveryScheduleConfig, scheduler

PREFIX = "/api/v1"
SCHED = f"{PREFIX}/hunting/discovery/schedule"
ADMIN = {"X-ORCA-User": "admin"}
ANA = {"X-ORCA-User": "ana"}


# --- config ---------------------------------------------------------------------


def test_schedule_config_disabled_by_default():
    cfg = DiscoveryScheduleConfig.from_env({})
    assert cfg.enabled is False
    assert cfg.interval_minutes == 60
    assert cfg.limit_per_aor == 10


def test_schedule_config_parses_env():
    cfg = DiscoveryScheduleConfig.from_env(
        {
            "ORCA_HUNTING_DISCOVERY_SCHEDULE_ENABLED": "true",
            "ORCA_HUNTING_DISCOVERY_SCHEDULE_INTERVAL_MINUTES": "15",
            "ORCA_HUNTING_DISCOVERY_SCHEDULE_LIMIT": "5",
        }
    )
    assert cfg.enabled is True
    assert cfg.interval_minutes == 15
    assert cfg.limit_per_aor == 5
    assert cfg.interval_seconds() == 900


def test_interval_has_a_floor():
    # A tiny interval can't busy-loop the source: there's a 60s floor.
    cfg = DiscoveryScheduleConfig(interval_minutes=0)
    assert cfg.interval_seconds() == 60


# --- status endpoint ------------------------------------------------------------


def test_schedule_status_default(client):
    body = client.get(SCHED, headers=ANA).json()
    assert body["enabled"] is False
    assert body["paused"] is False
    assert body["running"] is False
    assert body["runs"] == 0
    assert body["last_run_at"] is None


# --- kill-switch (pause / resume), admin-only -----------------------------------


def test_pause_and_resume_are_admin_only(client):
    assert client.post(f"{SCHED}/pause", headers=ANA).status_code == 403
    assert client.post(f"{SCHED}/resume", headers=ANA).status_code == 403

    paused = client.post(f"{SCHED}/pause", headers=ADMIN).json()
    assert paused["paused"] is True
    resumed = client.post(f"{SCHED}/resume", headers=ADMIN).json()
    assert resumed["paused"] is False


# --- run now --------------------------------------------------------------------


def test_run_now_requires_admin(client, monkeypatch):
    monkeypatch.setenv("ORCA_HUNTING_DISCOVERY_PROVIDER", "mock")
    monkeypatch.setenv("ORCA_HUNTING_DISCOVERY_AORS", "Rhode Island")
    assert client.post(f"{SCHED}/run-now", headers=ANA).status_code == 403


def test_run_now_sweeps_and_records(client, monkeypatch):
    monkeypatch.setenv("ORCA_HUNTING_DISCOVERY_PROVIDER", "mock")
    monkeypatch.setenv("ORCA_HUNTING_DISCOVERY_AORS", "Rhode Island,Connecticut")
    monkeypatch.setenv("ORCA_HUNTING_DISCOVERY_SCHEDULE_LIMIT", "2")
    resp = client.post(f"{SCHED}/run-now", headers=ADMIN)
    assert resp.status_code == 200, resp.text
    sweep = resp.json()
    assert sweep["total_proposed"] == 4  # 2 AORs x 2 candidates
    # The schedule record reflects the run.
    status = client.get(SCHED, headers=ADMIN).json()
    assert status["runs"] == 1
    assert status["last_total_proposed"] == 4
    assert status["last_aors"] == ["Rhode Island", "Connecticut"]
    assert status["last_error"] is None
    # The sources are now in the registry as proposed discovery jobs.
    sources = client.get(f"{PREFIX}/hunting/sources?status=proposed", headers=ADMIN).json()
    assert len(sources) == 4


def test_run_now_disabled_returns_400_and_records_error(client, monkeypatch):
    # Watchlist present so the provider's disabled-state is the surfaced error.
    monkeypatch.setenv("ORCA_HUNTING_DISCOVERY_AORS", "Rhode Island")
    monkeypatch.delenv("ORCA_HUNTING_DISCOVERY_PROVIDER", raising=False)
    resp = client.post(f"{SCHED}/run-now", headers=ADMIN)
    assert resp.status_code == 400
    status = client.get(SCHED, headers=ADMIN).json()
    assert status["last_error"] is not None
    assert "disabled" in status["last_error"].lower()
    assert status["runs"] == 0


def test_run_now_without_watchlist_returns_400(client, monkeypatch):
    monkeypatch.setenv("ORCA_HUNTING_DISCOVERY_PROVIDER", "mock")
    monkeypatch.delenv("ORCA_HUNTING_DISCOVERY_AORS", raising=False)
    resp = client.post(f"{SCHED}/run-now", headers=ADMIN)
    assert resp.status_code == 400
    assert "aor" in resp.json()["detail"].lower()


# --- the loop's run path (run_once) ---------------------------------------------


def test_run_once_records_run_and_is_audited(client, monkeypatch):
    # run_once is what the async loop calls each tick; exercise it directly (no timer).
    monkeypatch.setenv("ORCA_HUNTING_DISCOVERY_PROVIDER", "mock")
    monkeypatch.setenv("ORCA_HUNTING_DISCOVERY_AORS", "Rhode Island")
    sweep = scheduler.run_once()
    assert sweep is not None
    assert scheduler.runs == 1
    assert scheduler.last_error is None
    # Attributed to the system actor and recorded in the central audit log.
    entries = client.get(
        f"{PREFIX}/audit?action_prefix=hunting.discovery.sweep", headers=ADMIN
    ).json()
    assert any(e["actor_id"] == "system" for e in entries)


def test_run_once_swallows_discovery_error(monkeypatch):
    # A misconfigured cadence must not crash the loop — the error is recorded, not raised.
    monkeypatch.delenv("ORCA_HUNTING_DISCOVERY_PROVIDER", raising=False)
    result = scheduler.run_once()
    assert result is None
    assert scheduler.last_error is not None
    assert scheduler.runs == 0


# --- the cadence's collection pass (run_collection_once) -------------------------


AUTH = {
    "lawful_basis": "publicly available; licensed feed",
    "access_method": "licensed search API (read-only)",
    "jurisdiction": "Rhode Island, USA",
}


def _monitored(client, name="M", url="https://m.invalid"):
    src = f"{PREFIX}/hunting/sources"
    sid = client.post(
        src,
        json={"name": name, "url": url, "category": "escort_listing", "aor": "Rhode Island"},
        headers=ANA,
    ).json()["id"]
    client.post(f"{src}/{sid}/authorize", json=AUTH, headers=ADMIN)
    client.post(f"{src}/{sid}/monitor", headers=ADMIN)
    return sid


def test_run_collection_once_records_and_audits(client, monkeypatch):
    monkeypatch.setenv("ORCA_HUNTING_COLLECTION_PROVIDER", "mock")
    _monitored(client)
    sweep = scheduler.run_collection_once()
    assert sweep is not None
    assert scheduler.collection_runs == 1
    assert scheduler.last_collection_error is None
    status = client.get(SCHED, headers=ADMIN).json()
    assert status["collection_runs"] == 1
    assert status["last_collection_sources"] == 1
    entries = client.get(
        f"{PREFIX}/audit?action_prefix=hunting.collection.sweep", headers=ADMIN
    ).json()
    assert any(e["actor_id"] == "system" for e in entries)


def test_run_collection_once_swallows_error(monkeypatch):
    monkeypatch.delenv("ORCA_HUNTING_COLLECTION_PROVIDER", raising=False)
    assert scheduler.run_collection_once() is None
    assert scheduler.last_collection_error is not None
    assert scheduler.collection_runs == 0
