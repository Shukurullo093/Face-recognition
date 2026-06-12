"""Person entity — a real-world identity that owns one or more enrolled faces."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.face import Face


class Person(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "persons"

    # External/business identifier supplied by the caller (e.g. employee id).
    external_id: Mapped[str | None] = mapped_column(
        String(128), unique=True, index=True, nullable=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    faces: Mapped[list["Face"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
