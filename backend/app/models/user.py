"""User and case-membership ORM models (v0.4 Auth/RBAC, v0.6 case membership)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.rbac import CaseRole, MembershipStatus, Role
from app.models.base import Base, TimestampMixin, UUIDPrimaryKey
from app.models.types import pg_enum


class User(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(pg_enum(Role, "orca_role"), nullable=False)


class CaseMembership(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "case_members"
    # One membership row per (case, user). Re-adding a removed member reactivates the
    # same row, so there is never more than one membership — let alone one active — for
    # a given user in a given case.
    __table_args__ = (
        UniqueConstraint("case_id", "user_id", name="uq_case_member"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    case_role: Mapped[CaseRole] = mapped_column(pg_enum(CaseRole, "case_role"), nullable=False)
    status: Mapped[MembershipStatus] = mapped_column(
        pg_enum(MembershipStatus, "membership_status"),
        nullable=False,
        default=MembershipStatus.ACTIVE,
    )
    assigned_by: Mapped[str] = mapped_column(String(128), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
