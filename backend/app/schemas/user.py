"""User and case-membership API schemas (v0.4)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.rbac import Role
from app.schemas.common import ORCAModel


class UserRead(ORCAModel):
    id: UUID
    username: str
    display_name: str
    role: Role
    created_at: datetime


class CurrentUser(ORCAModel):
    """The authenticated principal plus the capabilities its role grants."""

    id: UUID
    username: str
    display_name: str
    role: Role
    capabilities: list[str]


class CaseMemberCreate(ORCAModel):
    username: str = Field(min_length=1, description="Username to assign to the case.")


class CaseMemberRead(ORCAModel):
    id: UUID
    case_id: UUID
    user_id: UUID
    username: str
    role: Role
    assigned_by: str
    assigned_at: datetime
