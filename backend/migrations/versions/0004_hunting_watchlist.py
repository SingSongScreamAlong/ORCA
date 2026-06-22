"""operator-managed AOR watchlist

Revision ID: 0004_hunting_watchlist
Revises: 0003_entity_identifier_types
Create Date: 2026-06-22 00:00:00

Persists the operator-managed AOR watchlist the autonomous discovery cadence sweeps. Mirrors
backend/db/sql/schema.sql.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_hunting_watchlist"
down_revision = "0003_entity_identifier_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hunting_watchlist",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("aor_key", sa.String(255), nullable=False, unique=True),
        sa.Column("aor", sa.String(255), nullable=False),
        sa.Column("added_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("hunting_watchlist")
