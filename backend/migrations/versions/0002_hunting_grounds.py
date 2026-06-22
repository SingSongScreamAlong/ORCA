"""hunting grounds registry + escalation persistence

Revision ID: 0002_hunting_grounds
Revises: 0001_initial
Create Date: 2026-06-22 00:00:00

Persists the Hunting Grounds source/NAI registry and the report-only CSAM-escalation channel.
Each row carries the indexed filter fields (status, aor) plus a JSONB ``document`` holding the
full read model (including the append-only history). Mirrors backend/db/sql/schema.sql.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_hunting_grounds"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _uuid():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "hunting_sources",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("aor", sa.String(255), nullable=False),
        sa.Column("document", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_hunting_sources_status", "hunting_sources", ["status"])
    op.create_index("ix_hunting_sources_aor", "hunting_sources", ["aor"])

    op.create_table(
        "hunting_escalations",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("aor", sa.String(255), nullable=False),
        sa.Column("document", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_hunting_escalations_status", "hunting_escalations", ["status"])
    op.create_index("ix_hunting_escalations_aor", "hunting_escalations", ["aor"])


def downgrade() -> None:
    op.drop_table("hunting_escalations")
    op.drop_table("hunting_sources")
