"""Audit log of every recognition action (enroll / verify / search)."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RecognitionAction(str, enum.Enum):
    REGISTER = "register"
    VERIFY = "verify"
    SEARCH = "search"
    IMPORT = "import"


class RecognitionLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "recognition_logs"

    action: Mapped[RecognitionAction] = mapped_column(
        Enum(
            RecognitionAction,
            name="recognition_action",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        index=True,
    )
    person_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    matched_face_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str | None] = mapped_column(String(512), nullable=True)
