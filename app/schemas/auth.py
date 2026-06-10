"""Auth-related schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.security import Role
from app.schemas.common import ORMModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Seconds until expiry")


class TokenPayload(BaseModel):
    sub: str
    role: Role


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=8, max_length=128)
    role: Role = Role.VIEWER


class UserRead(ORMModel):
    id: str
    username: str
    role: Role
    is_active: bool
