"""Entity ORM model — a real-world thing referenced by observations.

Entities are deduplicated by ``(entity_type, value)``.
"""

from __future__ import annotations

from sqlalchemy import Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey
from app.models.enums import EntityType
from app.models.types import pg_enum


class Entity(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("entity_type", "value", name="uq_entity_type_value"),
    )

    entity_type: Mapped[EntityType] = mapped_column(
        pg_enum(EntityType, "entity_type"), nullable=False
    )
    # Canonicalized value (e.g. E.164 for phone numbers).
    value: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
