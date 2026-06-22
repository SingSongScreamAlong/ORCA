"""add located-identifier entity types

Revision ID: 0003_entity_identifier_types
Revises: 0002_hunting_grounds
Create Date: 2026-06-22 00:00:00

Adds the located-identifier entity types extracted from lead text (email, crypto_address,
onion_service, url) to the ``entity_type`` enum. Additive and backward-compatible. Mirrors
backend/db/sql/schema.sql.
"""

from __future__ import annotations

from alembic import op

revision = "0003_entity_identifier_types"
down_revision = "0002_hunting_grounds"
branch_labels = None
depends_on = None

_NEW_VALUES = ("email", "crypto_address", "onion_service", "url")


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block on older PostgreSQL.
    with op.get_context().autocommit_block():
        for value in _NEW_VALUES:
            op.execute(f"ALTER TYPE entity_type ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # PostgreSQL has no DROP VALUE for enums; removing a label requires recreating the type.
    # These additive values are left in place on downgrade (harmless if unused).
    pass
