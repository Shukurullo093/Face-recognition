"""API key + external (3rd-party) search schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class ApiKeyRead(ORMModel):
    id: uuid.UUID
    name: str
    prefix: str
    is_active: bool
    created_by: str | None
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreated(ApiKeyRead):
    """Returned only at creation time — includes the raw key (shown once)."""

    key: str = Field(description="Raw API key — store it now, it is not retrievable later")


class ExternalSearchResponse(BaseModel):
    """Top-1 identification result for 3rd-party callers (may be no match)."""

    matched: bool
    person_id: uuid.UUID | None = None
    full_name: str | None = None
    similarity: float | None = None
    threshold: float
