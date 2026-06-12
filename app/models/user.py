"""Application user (for JWT auth + RBAC)."""
from __future__ import annotations

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import Role
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        # values_callable -> store the enum *value* ("admin"), matching the
        # lowercase labels in the PG type; default would store the NAME ("ADMIN").
        Enum(Role, name="user_role", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=Role.VIEWER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
