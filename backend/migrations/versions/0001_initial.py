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
    "screenshot", "document", "image", "video", "web_archive", "analyst_note", "partner_file", "other",
    name="evidence_type", create_type=False,
)
evidence_status = postgresql.ENUM(
    "proposed", "approved", "rejected", "needs_more_review", "quarantined",
    name="evidence_status", create_type=False,
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
    "proposed", "approved", "rejected", "needs_more_review", name="review_status", create_type=False
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
    "proposed_observation", "proposed_relationship", "proposed_cluster", "flagged_observation",
    name="review_item_type", create_type=False,
)
orca_role = postgresql.ENUM(
    "admin", "case_manager", "analyst", "reviewer", "viewer", "partner_export_viewer",
    name="orca_role", create_type=False,
)
case_role = postgresql.ENUM(
    "case_manager", "analyst", "reviewer", "viewer", "partner_export_viewer",
    name="case_role", create_type=False,
)
membership_status = postgresql.ENUM(
    "active", "inactive", "revoked", name="membership_status", create_type=False,
)

_ALL_ENUMS = [
    source_type, source_reliability, evidence_type, evidence_status, entity_type, relationship_type,
    origin, review_status, cluster_status, case_status, report_status, review_item_type, orca_role,
    case_role, membership_status,
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

    # Cases are created before observations/relationships/review_items (which reference them).
    op.create_table(
        "cases",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("status", case_status, nullable=False, server_default="open"),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("legal_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "observations",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("case_id", _uuid(), sa.ForeignKey("cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_id", _uuid(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("collector", sa.String(255), nullable=False),
        sa.Column("location", sa.String(512), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("status", review_status, nullable=False, server_default="proposed"),
        sa.Column("decided_by", sa.String(255), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("handling", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_observations_case", "observations", ["case_id"])
    op.create_index("ix_observations_status", "observations", ["status"])

    op.create_table(
        "evidence_items",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("case_id", _uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", _uuid(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("observation_id", _uuid(), sa.ForeignKey("observations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("evidence_type", evidence_type, nullable=False),
        sa.Column("storage_uri", sa.String(2048), nullable=True),
        sa.Column("original_filename", sa.String(1024), nullable=True),
        sa.Column("mime_type", sa.String(255), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("captured_by", sa.String(255), nullable=True),
        sa.Column("access_method", sa.String(64), nullable=False, server_default="manual_upload"),
        sa.Column("legal_flags", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("handling_notes", sa.Text(), nullable=True),
        sa.Column("status", evidence_status, nullable=False, server_default="proposed"),
        sa.Column("has_bytes", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_evidence_items_case", "evidence_items", ["case_id"])
    op.create_index("ix_evidence_items_observation", "evidence_items", ["observation_id"])
    op.create_index("ix_evidence_items_sha256", "evidence_items", ["sha256"])

    op.create_table(
        "relationships",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("case_id", _uuid(), sa.ForeignKey("cases.id", ondelete="SET NULL"), nullable=True),
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
    op.create_index("ix_relationships_case", "relationships", ["case_id"])

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
        "report_packages",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("case_id", _uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("status", report_status, nullable=False, server_default="final"),
        sa.Column("handling_level", sa.String(64), nullable=False),
        sa.Column("generated_by", sa.String(255), nullable=False),
        sa.Column("report_markdown", sa.Text(), nullable=False),
        sa.Column("manifest", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("report_sha256", sa.String(64), nullable=False),
        sa.Column("manifest_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_report_packages_case", "report_packages", ["case_id"])

    op.create_table(
        "review_items",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("item_type", review_item_type, nullable=False),
        sa.Column("subject_type", sa.String(64), nullable=False),
        sa.Column("subject_id", _uuid(), nullable=False),
        sa.Column("case_id", _uuid(), sa.ForeignKey("cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
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
        sa.Column("case_id", _uuid(), nullable=True),
        sa.Column("context", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("username", sa.String(128), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("role", orca_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "case_members",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("case_id", _uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", _uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_role", case_role, nullable=False),
        sa.Column("status", membership_status, nullable=False, server_default="active"),
        sa.Column("assigned_by", sa.String(128), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # One membership per (case, user); re-adding reactivates the same row.
        sa.UniqueConstraint("case_id", "user_id", name="uq_case_member"),
    )
    op.create_index("ix_case_members_user", "case_members", ["user_id"])
    op.create_index("ix_case_members_case", "case_members", ["case_id"])

    # Association tables.
    op.create_table(
        "observation_entities",
        sa.Column("observation_id", _uuid(), sa.ForeignKey("observations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("entity_id", _uuid(), sa.ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True),
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
    # Drop children before parents. Everything that references cases (observations,
    # relationships, review_items, reports) is dropped before cases itself.
    for table in (
        "case_clusters", "case_entities", "case_observations",
        "cluster_observations", "cluster_entities", "relationship_observations",
        "observation_entities", "case_members",
        "audit_log", "review_items", "report_packages", "reports", "evidence_items",
        "relationships", "observations", "clusters", "cases",
        "entities", "sources", "users",
    ):
        op.drop_table(table)

    bind = op.get_bind()
    for enum in reversed(_ALL_ENUMS):
        enum.drop(bind, checkfirst=True)
