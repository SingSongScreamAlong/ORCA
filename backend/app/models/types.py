"""Shared SQLAlchemy column helpers."""

from __future__ import annotations

from enum import Enum
from typing import TypeVar

from sqlalchemy import Enum as SAEnum

E = TypeVar("E", bound=Enum)


def pg_enum(enum_cls: type[E], name: str) -> SAEnum:
    """A PostgreSQL ENUM column that stores the enum *values* (lowercase).

    By default SQLAlchemy stores enum member *names*. We store ``.value`` instead so
    the database labels match the ontology and the API (e.g. ``phone_number``), keeping
    the ORM, the raw DDL, and the migration in agreement.
    """
    return SAEnum(
        enum_cls, name=name, values_callable=lambda enum: [member.value for member in enum]
    )
