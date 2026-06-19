"""initial ORCA schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00

Creates the full ORCA relational schema: enum types, core object tables, the
append-only audit log, and the association tables. Mirrors backend/db/sql/schema.sql.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

# Enum types are declared with create_type=False so we can create each exactly once
# (some are shared by multiple tables, e.g. ``origin`` and ``review_status``).
source_type = postgresql.ENUM(
    "website", "dataset", "manual_upload", "tip", "document", name="source_type", create_type=False
)
source_reliability = postgresql.ENUM(
    "unknown", "low", "medium", "high", name="source_reliability", create_type=False
)
evidence_type = postgresql.ENUM(
    "screenshot", "archived_page", "image", "file", "text", name="evidence_type", create_type=False
)
entity_type = postgresql.ENUM(
    "phone_number", "alias", "account", "username", "location", "vehicle", "image",
    "advertisement", "tattoo_marker", name="entity_type", create_type=False,
)
relationship_type = postgresql.ENUM(
    "shared_phone", "shared_image", "shared_location", "shared_account", "appears_with",
    "analyst_confirmed", name="relationship_type", create_type=False,
)
origin = postgresql.ENUM(
    "system_proposed", "analyst_created", "imported", name="origin", create_type=False
)
review_status = postgresql.ENUM(
    "proposed", "confirmed", "rejected", "needs_review", name="review_status", create_type=False
)
cluster_status = postgresql.ENUM(
    "proposed", "active", "archived", "rejected", name="cluster_status", create_type=False
)
case_status = postgresql.ENUM(
    "open", "active", "on_hold", "closed", name="case_status", create_type=False
)
report_status = postgresql.ENUM(
    "draft", "in_review", "final", name="report_status", create_type=False
)
review_item_type = postgresql.ENUM(
    "proposed_relationship", "proposed_cluster", "flagged_observation",
    name="review_item_type", create_type=False,
)

_ALL_ENUMS = [
    source_type, source_reliability, evidence_type, entity_type, relationship_type,
    origin, review_status, cluster_status, case_status, report_status, review_item_type,
]


def _uuid():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    bind = op.get_bind()
    for enum in _ALL_ENUMS:
        enum.create(bind, checkfirst=True)

    op.create_table(
        "sources",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("identifier", sa.String(2048), nullable=True),
        sa.Column("reliability", source_reliability, nullable=False, server_default="unknown"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "evidence",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("evidence_type", evidence_type, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_uri", sa.String(2048), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_id", _uuid(), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_evidence_sha256", "evidence", ["sha256"])

    op.create_table(
        "entities",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("entity_type", entity_type, nullable=False),
        sa.Column("value", sa.String(1024), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("entity_type", "value", name="uq_entity_type_value"),
    )
    op.create_index("ix_entities_value", "entities", ["value"])

    op.create_table(
        "observations",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_id", _uuid(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("collector", sa.String(255), nullable=False),
        sa.Column("location", sa.String(512), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "relationships",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("source_entity_id", _uuid(), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("target_entity_id", _uuid(), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("relationship_type", relationship_type, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("origin", origin, nullable=False, server_default="system_proposed"),
        sa.Column("status", review_status, nullable=False, server_default="proposed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("source_entity_id <> target_entity_id", name="ck_relationship_distinct_endpoints"),
    )

    op.create_table(
        "clusters",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("status", cluster_status, nullable=False, server_default="proposed"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("origin", origin, nullable=False, server_default="system_proposed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "cases",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("status", case_status, nullable=False, server_default="open"),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "reports",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("case_id", _uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("status", report_status, nullable=False, server_default="draft"),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "review_items",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("item_type", review_item_type, nullable=False),
        sa.Column("subject_type", sa.String(64), nullable=False),
        sa.Column("subject_id", _uuid(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("evidence_ids", postgresql.ARRAY(_uuid()), nullable=False, server_default="{}"),
        sa.Column("status", review_status, nullable=False, server_default="proposed"),
        sa.Column("decided_by", sa.String(255), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("actor_id", sa.String(255), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(64), nullable=False),
        sa.Column("context", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Association tables.
    op.create_table(
        "observation_entities",
        sa.Column("observation_id", _uuid(), sa.ForeignKey("observations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("entity_id", _uuid(), sa.ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "observation_evidence",
        sa.Column("observation_id", _uuid(), sa.ForeignKey("observations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("evidence_id", _uuid(), sa.ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "relationship_observations",
        sa.Column("relationship_id", _uuid(), sa.ForeignKey("relationships.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("observation_id", _uuid(), sa.ForeignKey("observations.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "cluster_entities",
        sa.Column("cluster_id", _uuid(), sa.ForeignKey("clusters.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("entity_id", _uuid(), sa.ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "cluster_observations",
        sa.Column("cluster_id", _uuid(), sa.ForeignKey("clusters.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("observation_id", _uuid(), sa.ForeignKey("observations.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "case_observations",
        sa.Column("case_id", _uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("observation_id", _uuid(), sa.ForeignKey("observations.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "case_entities",
        sa.Column("case_id", _uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("entity_id", _uuid(), sa.ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "case_clusters",
        sa.Column("case_id", _uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("cluster_id", _uuid(), sa.ForeignKey("clusters.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    for table in (
        "case_clusters", "case_entities", "case_observations",
        "cluster_observations", "cluster_entities", "relationship_observations",
        "observation_evidence", "observation_entities",
        "audit_log", "review_items", "reports", "cases", "clusters",
        "relationships", "observations", "entities", "evidence", "sources",
    ):
        op.drop_table(table)

    bind = op.get_bind()
    for enum in reversed(_ALL_ENUMS):
        enum.drop(bind, checkfirst=True)
