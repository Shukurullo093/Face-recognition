"""Face entity — a single enrolled face image and its 512-D ArcFace embedding.

The `faces` and `face_embeddings` concepts from the spec are unified into one
table here: the embedding is a first-class column (pgvector VECTOR(512)) on the
face row, which is the efficient layout for ANN search (no join on the hot path).
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Float, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.person import Person

EMBEDDING_DIM = 512


class Face(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "faces"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # L2-normalised 512-D ArcFace embedding. Cosine distance == 1 - dot product.
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)

    det_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    bbox: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Small JPEG crop of the face for gallery display (NULL for faces enrolled
    # before this column existed, or when the source image was unavailable).
    thumbnail: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    # Denormalized mirror of persons.is_active, kept in sync by DB triggers
    # (migration 0004). Enables a PARTIAL HNSW index for active-only 1:N search
    # so the active filter is a pre-filter on the index, not a post-filter that
    # silently drops recall. Authoritative source remains persons.is_active.
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    person: Mapped["Person"] = relationship(back_populates="faces")
