"""Legal and handling metadata.

These are deliberately lightweight *placeholder* fields. They let an analyst record
the lawful basis for an observation and flag material that needs legal review or
careful handling. They do NOT implement any sensitive-collection capability — see
``docs/safety_and_handling.md``.
"""

from __future__ import annotations

from app.schemas.common import ORCAModel


class Handling(ORCAModel):
    # Free-text statement of the lawful basis (e.g. "publicly available information").
    lawful_basis: str | None = None
    # Flags an item for legal review before it is relied upon.
    requires_legal_review: bool = False
    # Marks material the analyst considers sensitive (handling care required).
    sensitive: bool = False
    # Analyst handling notes.
    notes: str | None = None
