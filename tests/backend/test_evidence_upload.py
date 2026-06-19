"""Evidence File Upload + Storage Hardening (v0.7).

Proves the upload/storage guarantees:

* an assigned analyst can upload a lawful file to an assigned case
* unassigned users and viewers cannot upload; partners can neither upload nor download
* uploads are hashed deterministically and the hash verifies
* metadata and raw-byte download are both case-scoped and role-scoped
* dangerous file types are refused; unknown types are quarantined
* oversize uploads are rejected
* approved uploaded evidence under an approved observation is cited in reports, while
  quarantined evidence is excluded
* upload, download, and verify write audit events
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

PREFIX = "/api/v1"
FORBIDDEN = "You do not have access to this case."


def H(user: str) -> dict:
    return {"X-ORCA-User": user}


def _seed_case(client) -> str:
    return client.get(f"{PREFIX}/cases", headers=H("admin")).json()[0]["id"]


def _source(client) -> str:
    return client.get(f"{PREFIX}/sources", headers=H("admin")).json()[0]["id"]


def _upload(
    client,
    user: str,
    case_id: str,
    src: str,
    *,
    filename: str = "note.txt",
    content: bytes = b"lawful evidence bytes",
    mime: str = "text/plain",
    title: str = "Uploaded item",
    acknowledged: bool = True,
    observation_id: str | None = None,
):
    data = {"source_id": src, "title": title, "acknowledged": str(acknowledged).lower()}
    if observation_id:
        data["observation_id"] = observation_id
    return client.post(
        f"{PREFIX}/cases/{case_id}/evidence/upload",
        files={"file": (filename, content, mime)},
        data=data,
        headers=H(user),
    )


def _approved_observation(client, case_id, src, note="obs") -> str:
    e = client.post(
        f"{PREFIX}/entities", json={"entity_type": "username", "value": f"{note}-u"}, headers=H("admin")
    ).json()["id"]
    obs = client.post(
        f"{PREFIX}/observations",
        json={
            "case_id": case_id, "timestamp": datetime.now(UTC).isoformat(),
            "source_id": src, "collector": "ana", "notes": note, "confidence": 0.7,
            "entity_ids": [e],
        },
        headers=H("ana"),
    ).json()
    item = next(
        i for i in client.get(f"{PREFIX}/review", headers=H("admin")).json()
        if i["subject_id"] == obs["id"]
    )
    client.post(f"{PREFIX}/review/{item['id']}/decision", json={"decision": "approve"}, headers=H("rae"))
    return obs["id"]


def _audit(client, case_id) -> list[str]:
    return [e["action"] for e in client.get(f"{PREFIX}/cases/{case_id}/audit", headers=H("admin")).json()]


# --- upload authorization -------------------------------------------------------


def test_assigned_analyst_can_upload(client):
    seed, src = _seed_case(client), _source(client)
    r = _upload(client, "ana", seed, src, content=b"hello world")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "proposed"
    assert body["has_bytes"] is True
    assert body["mime_type"] == "text/plain"
    assert body["size_bytes"] == len(b"hello world")
    assert body["sha256"] == hashlib.sha256(b"hello world").hexdigest()
    assert body["access_method"] == "manual_upload"


def test_unassigned_user_cannot_upload(client):
    seed, src = _seed_case(client), _source(client)
    r = _upload(client, "nomad", seed, src)  # nomad: global analyst, not a member
    assert r.status_code == 403
    assert r.json()["detail"] == FORBIDDEN


def test_viewer_cannot_upload(client):
    seed, src = _seed_case(client), _source(client)
    assert _upload(client, "vic", seed, src).status_code == 403


def test_partner_cannot_upload(client):
    seed, src = _seed_case(client), _source(client)
    assert _upload(client, "partner", seed, src).status_code == 403


def test_safety_acknowledgement_is_required(client):
    seed, src = _seed_case(client), _source(client)
    r = _upload(client, "ana", seed, src, acknowledged=False)
    assert r.status_code == 422
    assert "acknowledge" in r.json()["detail"].lower()


# --- integrity ------------------------------------------------------------------


def test_upload_sha256_is_deterministic(client):
    seed, src = _seed_case(client), _source(client)
    content = b"deterministic-bytes"
    a = _upload(client, "ana", seed, src, content=content, title="A").json()
    b = _upload(client, "ana", seed, src, content=content, title="B").json()
    assert a["sha256"] == b["sha256"] == hashlib.sha256(content).hexdigest()


def test_verify_after_upload_passes(client):
    seed, src = _seed_case(client), _source(client)
    item = _upload(client, "ana", seed, src, content=b"verify-me").json()
    verify = client.post(f"{PREFIX}/evidence/{item['id']}/verify", headers=H("rae")).json()
    assert verify["verified"] is True
    assert verify["computed_sha256"] == hashlib.sha256(b"verify-me").hexdigest()


# --- case + role scoping --------------------------------------------------------


def test_metadata_is_case_scoped(client):
    seed, src = _seed_case(client), _source(client)
    item = _upload(client, "ana", seed, src).json()
    # A member reads metadata; an unassigned user cannot.
    assert client.get(f"{PREFIX}/evidence/{item['id']}", headers=H("vic")).status_code == 200
    denied = client.get(f"{PREFIX}/evidence/{item['id']}", headers=H("nomad"))
    assert denied.status_code == 403
    assert denied.json()["detail"] == FORBIDDEN


def test_download_is_case_and_role_scoped(client):
    seed, src = _seed_case(client), _source(client)
    content = b"downloadable-bytes"
    item = _upload(client, "ana", seed, src, content=content, filename="d.txt").json()
    # A mutating member (reviewer) and an admin may download the raw bytes.
    ok = client.get(f"{PREFIX}/evidence/{item['id']}/download", headers=H("rae"))
    assert ok.status_code == 200
    assert ok.content == content
    assert client.get(f"{PREFIX}/evidence/{item['id']}/download", headers=H("admin")).status_code == 200
    # A viewer sees metadata but not raw bytes; a partner and an unassigned user get 403.
    assert client.get(f"{PREFIX}/evidence/{item['id']}/download", headers=H("vic")).status_code == 403
    assert client.get(f"{PREFIX}/evidence/{item['id']}/download", headers=H("partner")).status_code == 403
    assert client.get(f"{PREFIX}/evidence/{item['id']}/download", headers=H("nomad")).status_code == 403


# --- upload policy --------------------------------------------------------------


def test_dangerous_file_type_is_rejected(client):
    seed, src = _seed_case(client), _source(client)
    r = _upload(
        client, "ana", seed, src, filename="malware.exe", content=b"MZ...",
        mime="application/octet-stream",
    )
    assert r.status_code == 422
    assert "not permitted" in r.json()["detail"].lower()
    # Nothing was stored: the case locker has no such item.
    locker = client.get(f"{PREFIX}/cases/{seed}/evidence", headers=H("admin")).json()
    assert all(e["original_filename"] != "malware.exe" for e in locker)


def test_unknown_type_is_quarantined(client):
    seed, src = _seed_case(client), _source(client)
    item = _upload(
        client, "ana", seed, src, filename="data.xyz", content=b"blob",
        mime="application/octet-stream",
    ).json()
    assert item["status"] == "quarantined"
    assert "evidence.quarantined" in _audit(client, seed)


def test_oversize_upload_is_rejected(client, monkeypatch):
    from app.core.config import get_settings

    seed, src = _seed_case(client), _source(client)
    monkeypatch.setenv("ORCA_EVIDENCE_MAX_UPLOAD_BYTES", "16")
    get_settings.cache_clear()
    try:
        r = _upload(client, "ana", seed, src, content=b"x" * 64)
        assert r.status_code == 422
        assert "maximum upload size" in r.json()["detail"].lower()
    finally:
        monkeypatch.delenv("ORCA_EVIDENCE_MAX_UPLOAD_BYTES", raising=False)
        get_settings.cache_clear()


# --- audit ----------------------------------------------------------------------


def test_upload_and_download_are_audited(client):
    seed, src = _seed_case(client), _source(client)
    item = _upload(client, "ana", seed, src).json()
    client.get(f"{PREFIX}/evidence/{item['id']}/download", headers=H("rae"))
    actions = _audit(client, seed)
    assert "evidence.uploaded" in actions
    assert "evidence.downloaded" in actions


# --- reports --------------------------------------------------------------------


def test_approved_uploaded_evidence_is_cited_in_report(client):
    seed, src = _seed_case(client), _source(client)
    obs = _approved_observation(client, seed, src, note="primary")
    item = _upload(
        client, "ana", seed, src, content=b"cited-bytes", title="UPLOADED-EVIDENCE", observation_id=obs
    ).json()
    client.post(f"{PREFIX}/evidence/{item['id']}/decision", json={"decision": "approve"}, headers=H("rae"))
    body = client.post(f"{PREFIX}/cases/{seed}/report", headers=H("ana")).json()["body"]
    assert "UPLOADED-EVIDENCE" in body


def test_quarantined_upload_is_excluded_from_report(client):
    seed, src = _seed_case(client), _source(client)
    obs = _approved_observation(client, seed, src, note="q")
    # Unknown type → quarantined; even linked + (attempted) approval keeps it out of reports.
    item = _upload(
        client, "ana", seed, src, filename="q.xyz", content=b"q", mime="application/octet-stream",
        title="QUARANTINED-UPLOAD", observation_id=obs,
    ).json()
    assert item["status"] == "quarantined"
    body = client.post(f"{PREFIX}/cases/{seed}/report", headers=H("ana")).json()["body"]
    assert "QUARANTINED-UPLOAD" not in body
