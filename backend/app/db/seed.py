"""Seed demo users into the active backend.

For the PostgreSQL backend, run after ``alembic upgrade head`` so authentication has
identities to resolve:

    python -m app.db.seed

The in-memory backend seeds these users automatically (see ``repositories/store.py``).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.core.rbac import Role
from app.repositories.uow import build_unit_of_work
from app.schemas.user import UserRead

DEMO_USERS = [
    ("admin", "Avery Admin", Role.ADMIN),
    ("casey", "Casey Manager", Role.CASE_MANAGER),
    ("ana", "Ana Analyst", Role.ANALYST),
    ("rae", "Rae Reviewer", Role.REVIEWER),
    ("vic", "Vic Viewer", Role.VIEWER),
    ("partner", "Partner Export", Role.PARTNER_EXPORT_VIEWER),
]


def seed_demo_users(uow) -> int:
    """Insert any missing demo users. Returns the number created."""
    created = 0
    for username, display, role in DEMO_USERS:
        if uow.users.get_by_username(username) is None:
            uow.users.add(
                UserRead(
                    id=uuid4(), username=username, display_name=display, role=role,
                    created_at=datetime.now(UTC),
                )
            )
            created += 1
    return created


def main() -> None:
    uow = build_unit_of_work()
    try:
        created = seed_demo_users(uow)
        uow.commit()
        print(f"Seeded {created} demo user(s).")
    finally:
        uow.close()


if __name__ == "__main__":
    main()
