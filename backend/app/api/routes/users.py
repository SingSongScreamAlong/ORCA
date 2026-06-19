"""User endpoints: the current principal, and the demo user roster (dev switcher)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import current_principal, get_uow
from app.core.rbac import capabilities_for
from app.core.security import Principal
from app.repositories.uow import UnitOfWork
from app.schemas.user import CurrentUser, UserRead

router = APIRouter(tags=["users"])


@router.get("/me", response_model=CurrentUser, summary="The authenticated principal and its capabilities")
def me(principal: Principal = Depends(current_principal)) -> CurrentUser:
    return CurrentUser(
        id=principal.id,
        username=principal.username,
        display_name=principal.display_name,
        role=principal.role,
        capabilities=capabilities_for(principal.role),
    )


@router.get("/users", response_model=list[UserRead], summary="List users (dev switcher roster)")
def list_users(
    _: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> list[UserRead]:
    return uow.users.list()
