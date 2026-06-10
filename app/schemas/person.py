"""Person request/response schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class PersonCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    external_id: str | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    external_id: str | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] | None = None
    is_active: bool | None = None


class PersonRead(ORMModel):
    id: uuid.UUID
    external_id: str | None
    full_name: str
    metadata: dict[str, Any] = Field(validation_alias="meta")
    is_active: bool
    created_at: datetime
    updated_at: datetime
