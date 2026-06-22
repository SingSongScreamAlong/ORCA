"""Identifier extraction — turn located lead text into structured entity hints.

"Locate, don't collect": ORCA reads the **text** of a lead (an ad/post summary) and pulls out the
*pointers and identifiers* that build a case — phone numbers, emails, crypto wallets, ``.onion``
services, URLs, @handles — never any media. This runs on **every** lead at ingestion (hand-logged,
clearnet collection, or any future dark-web source), so the located identifiers flow into ORCA's
entity graph automatically and cross-link the moment the same number/handle/wallet recurs.

Extractors are written for **precision over recall** — a false identifier is worse than a missed
one in a referral — and everything stays a *proposal* an analyst reviews. This module is pure and
side-effect free; the lead service resolves the hints into deduplicated entities.
"""

from __future__ import annotations

import re

from app.models.enums import EntityType
from app.schemas.hunting import HuntingEntityHint

_MAX_HINTS = 50  # a single lead can't explode the graph

# Order matters: onion before url (an .onion host is also URL-shaped); email before @handle.
_ONION = re.compile(r"\b((?:[a-z2-7]{16}|[a-z2-7]{56})\.onion)\b", re.IGNORECASE)
_URL = re.compile(r"\bhttps?://[^\s<>\"')]+", re.IGNORECASE)
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
# BTC (legacy base58 + bech32) and ETH — high-precision, anchored shapes.
_BTC = re.compile(r"\b(?:bc1[ac-hj-np-z02-9]{11,71}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b")
_ETH = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
# NANP phone: optional +1, area [2-9]xx, then 3+4 digits, not embedded in a longer digit run.
_PHONE = re.compile(
    r"(?<!\d)(?:\+?1[\s.\-]?)?\(?([2-9]\d{2})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})(?!\d)"
)
_HANDLE = re.compile(r"(?<!\w)@([A-Za-z0-9_]{3,32})\b")

_TRAILING = ".,;:!?)]}>\"'"


def _norm_phone(match: re.Match) -> str:
    return "+1" + match.group(1) + match.group(2) + match.group(3)


def extract_identifiers(text: str | None) -> list[HuntingEntityHint]:
    """Extract typed identifier hints from free lead text (deduplicated, capped). Never media."""
    if not text:
        return []

    found: list[tuple[EntityType, str]] = []

    for m in _ONION.finditer(text):
        found.append((EntityType.ONION_SERVICE, m.group(1).lower()))
    for m in _URL.finditer(text):
        found.append((EntityType.URL, m.group(0).rstrip(_TRAILING)))
    for m in _EMAIL.finditer(text):
        found.append((EntityType.EMAIL, m.group(0).lower()))
    for m in _BTC.finditer(text):
        found.append((EntityType.CRYPTO_ADDRESS, m.group(0)))
    for m in _ETH.finditer(text):
        # Lower-case so mixed-case (EIP-55 checksummed) variants of one address dedup together.
        found.append((EntityType.CRYPTO_ADDRESS, m.group(0).lower()))
    for m in _PHONE.finditer(text):
        found.append((EntityType.PHONE_NUMBER, _norm_phone(m)))
    for m in _HANDLE.finditer(text):
        found.append((EntityType.USERNAME, m.group(1)))

    # Deduplicate by (type, value), preserving first-seen order; cap the total.
    seen: set[tuple[EntityType, str]] = set()
    hints: list[HuntingEntityHint] = []
    for entity_type, value in found:
        key = (entity_type, value)
        if value and key not in seen:
            seen.add(key)
            hints.append(HuntingEntityHint(entity_type=entity_type, value=value))
        if len(hints) >= _MAX_HINTS:
            break
    return hints
