"""Hunting Grounds privileged actions are written to ORCA's append-only audit log, and the
admin-only system audit endpoint surfaces them (case-less integration actions included)."""

from __future__ import annotations

PREFIX = "/api/v1"
SRC = f"{PREFIX}/hunting/sources"
ADMIN = {"X-ORCA-User": "admin"}

AUTH = {
    "lawful_basis": "publicly available information",
    "access_method": "licensed search API (read-only)",
    "jurisdiction": "Rhode Island, USA",
}


def _audit(client, prefix="hunting."):
    return client.get(f"{PREFIX}/audit?action_prefix={prefix}", headers=ADMIN).json()


def test_source_lifecycle_is_audited(client):
    sid = client.post(
        SRC,
        json={"name": "S", "url": "https://s.invalid", "category": "escort_listing", "aor": "Rhode Island"},
        headers={"X-ORCA-User": "ana"},
    ).json()["id"]
    client.post(f"{SRC}/{sid}/authorize", json=AUTH, headers=ADMIN)
    client.post(f"{SRC}/{sid}/monitor", headers=ADMIN)

    actions = [e["action"] for e in _audit(client)]
    assert "hunting.source.proposed" in actions
    assert "hunting.source.authorized" in actions
    assert "hunting.source.monitored" in actions
    # The audited entries are attributable and case-less (integration actions).
    entry = next(e for e in _audit(client) if e["action"] == "hunting.source.authorized")
    assert entry["target_type"] == "hunting_source"
    assert entry["case_id"] is None


def test_escalation_is_audited(client):
    client.post(
        f"{PREFIX}/hunting/escalations",
        json={"aor": "Rhode Island", "concern": "Appears to depict a minor."},
        headers={"X-ORCA-User": "ana"},
    )
    actions = [e["action"] for e in _audit(client, "hunting.escalation")]
    assert "hunting.escalation.open" in actions


def test_system_audit_is_admin_only(client):
    for user in ("ana", "rae", "vic", "partner"):
        assert client.get(f"{PREFIX}/audit", headers={"X-ORCA-User": user}).status_code == 403
    assert client.get(f"{PREFIX}/audit", headers=ADMIN).status_code == 200
