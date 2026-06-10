"""Shared schema primitives."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Base for response models that map from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1
