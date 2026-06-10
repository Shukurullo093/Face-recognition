"""Face enrollment / verification / identification schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import BoundingBox, ORMModel


# ---- Enrollment ----
class FaceRegisterResponse(BaseModel):
    face_id: uuid.UUID
    person_id: uuid.UUID
    embedding_generated: bool = True
    confidence: float = Field(description="Detection score of the enrolled face")
    bbox: BoundingBox


class FaceRead(ORMModel):
    id: uuid.UUID
    person_id: uuid.UUID
    det_score: float
    quality: float | None
    image_path: str | None
    created_at: datetime


class FaceGalleryItem(BaseModel):
    """One face for the dashboard gallery: thumbnail + full embedding vector."""

    id: uuid.UUID
    person_id: uuid.UUID
    full_name: str
    det_score: float
    quality: float | None
    image_path: str | None
    created_at: datetime
    thumbnail: str | None = Field(default=None, description="data:image/jpeg;base64 URI or null")
    embedding: list[float] = Field(description="512-D L2-normalised vector")
    embedding_dim: int
    embedding_norm: float


# ---- Verification (1:1) ----
class VerifyResponse(BaseModel):
    matched: bool
    similarity_score: float = Field(description="Best cosine similarity vs the person's faces")
    threshold: float
    person_id: uuid.UUID
    matched_face_id: uuid.UUID | None = None


# ---- Identification (1:N) ----
class SearchMatch(BaseModel):
    person_id: uuid.UUID
    face_id: uuid.UUID
    full_name: str
    similarity_score: float


class SearchResponse(BaseModel):
    matches: list[SearchMatch]
    threshold: float
    query_confidence: float = Field(description="Detection score of the query face")


# ---- Bulk import ----
class ImportRequest(BaseModel):
    """Import from a server-side folder whose subdirectories are person names.

    Layout:  <root>/<person_name>/<image1.jpg, image2.jpg, ...>
    """

    root_path: str = Field(description="Absolute path on the server, mounted into the container")
    use_dir_as_person: bool = Field(
        default=True,
        description="If true each subdirectory becomes a Person (full_name = dir name)",
    )


class ImportJobStatus(BaseModel):
    job_id: uuid.UUID
    state: str  # pending | running | completed | failed
    total: int
    processed: int
    succeeded: int
    failed: int
    errors: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @property
    def progress(self) -> float:
        return 0.0 if self.total == 0 else round(self.processed / self.total, 4)
