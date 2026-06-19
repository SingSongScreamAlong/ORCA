"""User and case-membership API schemas (v0.4 identities, v0.6 case membership)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.rbac import CaseRole, MembershipStatus, Role
from app.schemas.common import ORCAModel


class UserRead(ORCAModel):
    id: UUID
    username: str
    display_name: str
    role: Role
    created_at: datetime


class CurrentUser(ORCAModel):
    """The authenticated principal plus the capabilities its global role grants."""

    id: UUID
    username: str
    display_name: str
    role: Role
    capabilities: list[str]


class CaseMemberRead(ORCAModel):
    """A user's membership in a case. Joins the user's identity for display."""

    id: UUID  # the membership id
    case_id: UUID
    user_id: UUID
    username: str
    display_name: str
    global_role: Role
    case_role: CaseRole
    status: MembershipStatus
    assigned_by: str
    assigned_at: datetime
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CaseMemberCreate(ORCAModel):
    """Assign a user to a case. ``case_role`` defaults to the user's global role."""

    username: str = Field(min_length=1, description="Username to assign to the case.")
    case_role: CaseRole | None = Field(
        default=None, description="Role within this case. Defaults from the user's global role."
    )
    notes: str | None = Field(default=None, description="Optional assignment note.")


class CaseMemberUpdate(ORCAModel):
    """Change a membership's case role and/or status (admin or the case's manager)."""

    case_role: CaseRole | None = None
    status: MembershipStatus | None = None
    notes: str | None = None
