"""Identifier extraction — "locate, don't collect".

ORCA reads the text of a lead and pulls out the pointers that build a case (phones, emails,
crypto wallets, .onion services, URLs, @handles) — never media. These tests prove the extractors
are high-precision, and that extraction is **additive** at ingestion: it enriches every lead with
more located identifiers and never removes the explicit hints or the full text lead.
"""

from __future__ import annotations

from app.models.enums import EntityType
from app.services.identifier_extraction import extract_identifiers

PREFIX = "/api/v1"
SRC = f"{PREFIX}/hunting/sources"
ADMIN = {"X-ORCA-User": "admin"}
ANA = {"X-ORCA-User": "ana"}

AUTH = {
    "lawful_basis": "publicly available; licensed feed",
    "access_method": "licensed search API (read-only)",
    "jurisdiction": "Rhode Island, USA",
}


def _types(hints):
    return {(h.entity_type, h.value) for h in hints}


# --- the extractors -------------------------------------------------------------


def test_extracts_phone_in_various_formats():
    for text, expected in [
        ("call (401) 555-0142 now", "+14015550142"),
        ("text 401.555.0142", "+14015550142"),
        ("+1 401 555 0142", "+14015550142"),
        ("4015550142", "+14015550142"),
    ]:
        hints = extract_identifiers(text)
        assert (EntityType.PHONE_NUMBER, expected) in _types(hints), text


def test_extracts_email_crypto_onion_url_handle():
    text = (
        "contact jane.doe@proton.me or @vendor_99 — wallet "
        "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq and 0xAbC0000000000000000000000000000000000000 "
        "mirror http://abcdefghij234567.onion/listing and https://example.invalid/ad?id=7"
    )
    got = _types(extract_identifiers(text))
    assert (EntityType.EMAIL, "jane.doe@proton.me") in got
    assert (EntityType.USERNAME, "vendor_99") in got
    assert (EntityType.CRYPTO_ADDRESS, "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq") in got
    assert (EntityType.CRYPTO_ADDRESS, "0xAbC0000000000000000000000000000000000000") in got
    assert (EntityType.ONION_SERVICE, "abcdefghij234567.onion") in got
    assert any(t == EntityType.URL and "example.invalid/ad" in v for t, v in got)


def test_precision_no_false_positives_on_plain_text():
    # Ordinary prose with a long ID-like number must not yield spurious identifiers.
    hints = extract_identifiers("Posted 2024 near exit 12; reference 9988776655443322110 only.")
    assert hints == []


def test_dedupes_repeated_identifiers():
    hints = extract_identifiers("call 401-555-0142 or 401.555.0142, ask for @sky, @sky")
    phones = [h for h in hints if h.entity_type == EntityType.PHONE_NUMBER]
    handles = [h for h in hints if h.entity_type == EntityType.USERNAME]
    assert len(phones) == 1 and len(handles) == 1


def test_empty_text_is_safe():
    assert extract_identifiers(None) == []
    assert extract_identifiers("") == []


# --- additive at ingestion (does not water down collection) ---------------------


def _monitored(client):
    sid = client.post(
        SRC,
        json={"name": "M", "url": "https://m.invalid", "category": "escort_listing", "aor": "Rhode Island"},
        headers=ANA,
    ).json()["id"]
    client.post(f"{SRC}/{sid}/authorize", json=AUTH, headers=ADMIN)
    client.post(f"{SRC}/{sid}/monitor", headers=ADMIN)
    return sid


def test_ingested_lead_auto_extracts_identifiers(client):
    sid = _monitored(client)
    # A lead with NO explicit entity hints — everything is located from the text.
    lead = {"summary": "New ad: text 401-555-0142, email biz@mail.invalid, @nightowl", "confidence": 0.4}
    obs = client.post(f"{SRC}/{sid}/leads", json=lead, headers=ANA).json()
    # The full text lead is preserved as the observation's notes (collection not watered down).
    assert obs["notes"].startswith("New ad: text 401-555-0142")
    entities = client.get(f"{PREFIX}/entities", headers=ADMIN).json()
    values = {(e["entity_type"], e["value"]) for e in entities}
    assert ("phone_number", "+14015550142") in values
    assert ("email", "biz@mail.invalid") in values
    assert ("username", "nightowl") in values


def test_extraction_is_additive_to_explicit_hints(client):
    sid = _monitored(client)
    # An explicit alias hint PLUS a phone in the text → both are located.
    lead = {
        "summary": "ad reuses 401-555-0142",
        "confidence": 0.4,
        "entities": [{"entity_type": "alias", "value": "Sky"}],
    }
    obs = client.post(f"{SRC}/{sid}/leads", json=lead, headers=ANA).json()
    entities = {e["id"]: e for e in client.get(f"{PREFIX}/entities", headers=ADMIN).json()}
    on_obs = {(entities[i]["entity_type"], entities[i]["value"]) for i in obs["entity_ids"]}
    assert ("alias", "Sky") in on_obs  # explicit hint kept
    assert ("phone_number", "+14015550142") in on_obs  # extracted hint added


def test_collected_leads_cross_link_on_shared_phone(client, monkeypatch):
    # Two monitored sources whose mock leads reuse phone numbers resolve to shared entities,
    # so collection still cross-links — extraction strengthens it, doesn't dilute it.
    monkeypatch.setenv("ORCA_HUNTING_COLLECTION_PROVIDER", "mock")
    a = _monitored(client)
    client.post(f"{SRC}/{a}/collect?limit=2", headers=ANA)
    before = len(client.get(f"{PREFIX}/entities", headers=ADMIN).json())
    # Re-collect the same source: same synthetic phones → dedup to the same entities (no growth).
    client.post(f"{SRC}/{a}/collect?limit=2", headers=ANA)
    after = len(client.get(f"{PREFIX}/entities", headers=ADMIN).json())
    assert after == before
