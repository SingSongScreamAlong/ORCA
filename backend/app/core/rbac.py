"""Role-based access control.

Three roles, least privilege, separation of duties. Authorization is intended to be
checked at the service boundary so it applies regardless of which endpoint is used.
See ``docs/security.md``.
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    ADMIN = "admin"


# Capabilities are coarse-grained for the skeleton. They name what a role may do; the
# service layer maps operations to the capability they require.
class Capability(str, Enum):
    CREATE_OBSERVATION = "create_observation"
    CREATE_ENTITY = "create_entity"
    PROPOSE_RELATIONSHIP = "propose_relationship"
    REVIEW_DECIDE = "review_decide"  # approve / reject items in the review queue
    MANAGE_CASE = "manage_case"
    MANAGE_USERS = "manage_users"


_ROLE_CAPABILITIES: dict[Role, set[Capability]] = {
    Role.ANALYST: {
        Capability.CREATE_OBSERVATION,
        Capability.CREATE_ENTITY,
        Capability.PROPOSE_RELATIONSHIP,
        Capability.MANAGE_CASE,
    },
    Role.REVIEWER: {
        Capability.CREATE_OBSERVATION,
        Capability.CREATE_ENTITY,
        Capability.PROPOSE_RELATIONSHIP,
        Capability.MANAGE_CASE,
        Capability.REVIEW_DECIDE,
    },
    Role.ADMIN: set(Capability),  # all capabilities
}


def can(role: Role, capability: Capability) -> bool:
    """Return whether ``role`` is granted ``capability``."""
    return capability in _ROLE_CAPABILITIES.get(role, set())
