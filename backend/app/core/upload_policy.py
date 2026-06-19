"""Evidence upload policy (v0.7).

A small, pure, testable classifier that decides what happens to a manually uploaded
file, *before* its bytes are trusted. Safe-by-default:

* a dangerous extension (executable / script) is **rejected** — never stored;
* an allow-listed MIME type is **accepted** (stored, status proposed);
* anything else is **quarantined** — stored but isolated pending a reviewer decision.

The classifier never executes, decodes, or renders content. Size enforcement happens at
the request boundary (the route streams with a cap); this module judges type only. See
``docs/v0.7_evidence_file_upload.md`` and ``docs/safety_and_handling.md``.
"""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath


class UploadDecision(str, Enum):
    ACCEPT = "accept"
    QUARANTINE = "quarantine"
    REJECT = "reject"


@dataclass(frozen=True)
class UploadAssessment:
    effective_mime: str
    decision: UploadDecision
    reason: str


def guess_mime(filename: str, declared: str | None) -> str:
    """Best-effort MIME from the filename extension, then the declared type, then octet."""
    guessed = mimetypes.guess_type(filename)[0]
    return (guessed or (declared or "application/octet-stream")).lower()


def assess_upload(
    filename: str,
    declared_mime: str | None,
    *,
    allowed_mimes: set[str],
    blocked_extensions: set[str],
) -> UploadAssessment:
    """Classify an upload by filename + declared type against the configured policy."""
    suffix = PurePosixPath(filename or "").suffix.lower()
    mime = guess_mime(filename, declared_mime)

    if suffix and suffix in blocked_extensions:
        return UploadAssessment(
            mime, UploadDecision.REJECT, f"File type '{suffix}' is not permitted."
        )
    if mime in allowed_mimes:
        return UploadAssessment(mime, UploadDecision.ACCEPT, "Allowed file type.")
    return UploadAssessment(
        mime,
        UploadDecision.QUARANTINE,
        f"Type '{mime}' is not on the allow-list; stored quarantined pending review.",
    )
