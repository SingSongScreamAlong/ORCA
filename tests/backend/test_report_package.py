"""Report Package Export (v0.8).

Proves the export/packaging guarantees:

* a package includes approved observations/relationships/evidence only
* proposed / rejected / quarantined material is excluded
* the manifest carries SHA-256 + source metadata, and recorded hashes match the bytes
* a partner export viewer can view/download the approved package but no raw material
* an unassigned user is refused; partners cannot generate
* generation and downloads are audited
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime

PREFIX = "/api/v1"
FORBIDDEN = "You do not have access to this case."


def H(user: str) -> dict:
    return {"X-ORCA-User": user}


def _seed_case(client) -> str:
    return client.get(f"{PREFIX}/cases", headers=H("admin")).json()[0]["id"]


def _source(client) -> str:
    return client.get(f"{PREFIX}/sources", headers=H("admin")).json()[0]["id"]


def _fresh_case(client) -> str:
    """A new case (no seed evidence) with ana=analyst and rae=reviewer assigned."""
    cid = client.post(
        f"{PREFIX}/cases", json={"title": "Package case", "owner": "admin"}, headers=H("admin")
    ).json()["id"]
    for user, role in (("ana", "analyst"), ("rae", "reviewer")):
        client.post(
            f"{PREFIX}/cases/{cid}/members", json={"username": user, "case_role": role}, headers=H("admin")
        )
    return cid


def _approved_obs(client, case_id, src, note) -> str:
    e = client.post(
        f"{PREFIX}/entities", json={"entity_type": "username", "value": f"{note}-u"}, headers=H("ana")
    ).json()["id"]
    obs = client.post(
        f"{PREFIX}/observations",
        json={
            "case_id": case_id, "timestamp": datetime.now(UTC).isoformat(), "source_id": src,
            "collector": "ana", "notes": note, "confidence": 0.7, "entity_ids": [e],
        },
        headers=H("ana"),
    ).json()
    item = next(
        i for i in client.get(f"{PREFIX}/review", headers=H("admin")).json()
        if i["subject_id"] == obs["id"]
    )
    client.post(f"{PREFIX}/review/{item['id']}/decision", json={"decision": "approve"}, headers=H("rae"))
    return obs["id"]


def _proposed_obs(client, case_id, src, note) -> str:
    e = client.post(
        f"{PREFIX}/entities", json={"entity_type": "alias", "value": f"{note}-a"}, headers=H("ana")
    ).json()["id"]
    return client.post(
        f"{PREFIX}/observations",
        json={
            "case_id": case_id, "timestamp": datetime.now(UTC).isoformat(), "source_id": src,
            "collector": "ana", "notes": note, "confidence": 0.5, "entity_ids": [e],
        },
        headers=H("ana"),
    ).json()["id"]


def _reject_obs(client, obs_id):
    item = next(
        i for i in client.get(f"{PREFIX}/review", headers=H("admin")).json()
        if i["subject_id"] == obs_id
    )
    client.post(f"{PREFIX}/review/{item['id']}/decision", json={"decision": "reject"}, headers=H("rae"))


def _upload(
    client, case_id, src, *, title, content=b"evidence", filename="e.txt",
    mime="text/plain", obs=None,
):
    data = {"source_id": src, "title": title, "acknowledged": "true"}
    if obs:
        data["observation_id"] = obs
    return client.post(
        f"{PREFIX}/cases/{case_id}/evidence/upload",
        files={"file": (filename, content, mime)},
        data=data,
        headers=H("ana"),
    ).json()


def _decide_ev(client, ev_id, decision):
    client.post(f"{PREFIX}/evidence/{ev_id}/decision", json={"decision": decision}, headers=H("rae"))


def _generate(client, case_id, user="ana"):
    return client.post(f"{PREFIX}/cases/{case_id}/report/package", headers=H(user))


def _audit(client, case_id) -> list[str]:
    return [e["action"] for e in client.get(f"{PREFIX}/cases/{case_id}/audit", headers=H("admin")).json()]


# --- content selection ----------------------------------------------------------


def test_package_includes_approved_observations_only(client):
    seed, src = _seed_case(client), _source(client)
    _approved_obs(client, seed, src, "APPROVED-OBS")
    _proposed_obs(client, seed, src, "PROPOSED-OBS")
    _reject_obs(client, _proposed_obs(client, seed, src, "REJECTED-OBS"))

    pkg = _generate(client, seed).json()
    md = client.get(f"{PREFIX}/report-packages/{pkg['id']}/report", headers=H("ana")).text
    assert "APPROVED-OBS" in md
    assert "PROPOSED-OBS" not in md
    assert "REJECTED-OBS" not in md


def test_only_approved_evidence_is_cited(client):
    seed, src = _fresh_case(client), _source(client)
    obs = _approved_obs(client, seed, src, "ev-host")
    approved = _upload(client, seed, src, title="APPROVED-EV", content=b"a", obs=obs)
    rejected = _upload(client, seed, src, title="REJECTED-EV", content=b"b", obs=obs)
    # An unknown type is stored quarantined and must stay excluded from the package.
    _upload(client, seed, src, title="QUAR-EV", content=b"c", filename="q.xyz",
            mime="application/octet-stream", obs=obs)
    _decide_ev(client, approved["id"], "approve")
    _decide_ev(client, rejected["id"], "reject")

    pkg = _generate(client, seed).json()
    manifest = json.loads(client.get(f"{PREFIX}/report-packages/{pkg['id']}/manifest", headers=H("ana")).text)
    titles = {e["title"] for e in manifest["evidence"]}
    assert "APPROVED-EV" in titles
    assert "REJECTED-EV" not in titles
    assert "QUAR-EV" not in titles
    assert pkg["counts"]["cited_evidence"] == 1


def test_manifest_carries_sha_and_source_metadata(client):
    seed, src = _seed_case(client), _source(client)
    obs = _approved_obs(client, seed, src, "m-host")
    content = b"manifest evidence bytes"
    ev = _upload(client, seed, src, title="M-EV", content=content, obs=obs)
    _decide_ev(client, ev["id"], "approve")

    pkg = _generate(client, seed).json()
    manifest = json.loads(client.get(f"{PREFIX}/report-packages/{pkg['id']}/manifest", headers=H("ana")).text)
    entry = next(e for e in manifest["evidence"] if e["title"] == "M-EV")
    assert entry["sha256"] == hashlib.sha256(content).hexdigest()
    assert entry["source_id"] == src
    assert entry["source_name"]
    assert entry["mime_type"] == "text/plain"
    assert entry["size_bytes"] == len(content)
    assert entry["status"] == "approved"
    assert entry["verification"] == "verified"


def test_recorded_hashes_match_downloads(client):
    seed, src = _seed_case(client), _source(client)
    _approved_obs(client, seed, src, "hash-host")
    pkg = _generate(client, seed).json()
    md = client.get(f"{PREFIX}/report-packages/{pkg['id']}/report", headers=H("ana")).text
    manifest_text = client.get(f"{PREFIX}/report-packages/{pkg['id']}/manifest", headers=H("ana")).text
    assert hashlib.sha256(md.encode()).hexdigest() == pkg["report_sha256"]
    assert hashlib.sha256(manifest_text.encode()).hexdigest() == pkg["manifest_sha256"]


def test_zip_contains_report_and_manifest(client):
    seed, src = _seed_case(client), _source(client)
    _approved_obs(client, seed, src, "zip-host")
    pkg = _generate(client, seed).json()
    resp = client.get(f"{PREFIX}/report-packages/{pkg['id']}/package", headers=H("ana"))
    assert resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        assert set(zf.namelist()) == {"report.md", "manifest.json"}


# --- partner access -------------------------------------------------------------


def test_partner_can_access_package_but_not_raw_material(client):
    seed, src = _seed_case(client), _source(client)
    _approved_obs(client, seed, src, "partner-host")
    pkg = _generate(client, seed).json()

    # Partner (assigned to the seed case) can list, view, and download the package.
    listed = client.get(f"{PREFIX}/report-packages", headers=H("partner")).json()
    assert any(p["id"] == pkg["id"] for p in listed)
    base = f"{PREFIX}/report-packages/{pkg['id']}"
    for path in ("", "/report", "/manifest", "/package"):
        assert client.get(base + path, headers=H("partner")).status_code == 200, path

    # But never raw evidence, the graph, the audit log, or observations.
    for path in (f"/cases/{seed}/evidence", f"/cases/{seed}/graph", f"/cases/{seed}/audit",
                 f"/cases/{seed}/observations"):
        assert client.get(f"{PREFIX}{path}", headers=H("partner")).status_code == 403, path
    # And partners cannot generate a package.
    assert _generate(client, seed, user="partner").status_code == 403


def test_unassigned_user_is_refused(client):
    seed, src = _seed_case(client), _source(client)
    _approved_obs(client, seed, src, "nomad-host")
    pkg = _generate(client, seed).json()
    # nomad is not a member of any case.
    assert client.get(f"{PREFIX}/report-packages", headers=H("nomad")).json() == []
    denied = client.get(f"{PREFIX}/report-packages/{pkg['id']}", headers=H("nomad"))
    assert denied.status_code == 403
    assert denied.json()["detail"] == FORBIDDEN
    assert _generate(client, seed, user="nomad").status_code == 403


# --- audit ----------------------------------------------------------------------


def test_generation_and_downloads_are_audited(client):
    seed, src = _seed_case(client), _source(client)
    _approved_obs(client, seed, src, "audit-host")
    pkg = _generate(client, seed).json()
    client.get(f"{PREFIX}/report-packages/{pkg['id']}/report", headers=H("ana"))
    client.get(f"{PREFIX}/report-packages/{pkg['id']}/manifest", headers=H("ana"))
    client.get(f"{PREFIX}/report-packages/{pkg['id']}/package", headers=H("ana"))
    actions = _audit(client, seed)
    assert "report_package.generated" in actions
    assert "report_package.report_downloaded" in actions
    assert "report_package.manifest_downloaded" in actions
    assert "report_package.downloaded" in actions
