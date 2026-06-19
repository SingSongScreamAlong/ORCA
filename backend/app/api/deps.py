"""Shared API dependencies: pagination, the unit of work, authentication, and the
capability-based route guard."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass

from fastapi import Depends, Header, Query

from app.core.rbac import Capability, can
from app.core.security import Principal, resolve_principal
from app.repositories.uow import UnitOfWork, build_unit_of_work


def get_uow() -> Iterator[UnitOfWork]:
    """Yield a request-scoped unit of work, committing on success."""
    uow = build_unit_of_work()
    try:
        yield uow
        uow.commit()
    except Exception:
        uow.rollback()
        raise
    finally:
        uow.close()


def current_principal(
    x_orca_user: str | None = Header(default=None, alias="X-ORCA-User"),
    uow: UnitOfWork = Depends(get_uow),
) -> Principal:
    """Resolve the authenticated principal from the ``X-ORCA-User`` header (dev auth)."""
    return resolve_principal(x_orca_user, uow)


def require(capability: Capability) -> Callable[..., Principal]:
    """Return a dependency that requires ``capability`` and yields the principal.

    A missing capability raises ``PermissionDenied`` (HTTP 403).
    """

    def guard(principal: Principal = Depends(current_principal)) -> Principal:
        if not can(principal.role, capability):
            from app.services.errors import PermissionDenied

            raise PermissionDenied(
                f"Role '{principal.role.value}' is not permitted to {capability.value.replace('_', ' ')}."
            )
        return principal

    return guard


@dataclass
class Pagination:
    limit: int
    offset: int


def pagination(
    limit: int = Query(50, ge=1, le=200, description="Maximum items to return."),
    offset: int = Query(0, ge=0, description="Items to skip."),
) -> Pagination:
    return Pagination(limit=limit, offset=offset)
