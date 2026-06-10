"""Authentication service: credential check + token issuance + user creation."""
from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import AuthenticationError, EntityConflictError
from app.core.security import (
    Role,
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import Token, UserCreate


class AuthService:
    def __init__(self, user_repo: UserRepository, settings: Settings) -> None:
        self.users = user_repo
        self.settings = settings

    async def authenticate(self, username: str, password: str) -> Token:
        user = await self.users.get_by_username(username)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Incorrect username or password")
        if not user.is_active:
            raise AuthenticationError("User is disabled")

        token = create_access_token(subject=user.username, role=user.role)
        return Token(
            access_token=token,
            expires_in=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def create_user(self, payload: UserCreate) -> User:
        if await self.users.get_by_username(payload.username):
            raise EntityConflictError(f"Username '{payload.username}' already exists")
        user = User(
            username=payload.username,
            hashed_password=hash_password(payload.password),
            role=payload.role,
        )
        return await self.users.add(user)

    async def ensure_bootstrap_admin(self, username: str, password: str) -> None:
        """Create the first admin if no users exist yet (idempotent)."""
        if await self.users.get_by_username(username):
            return
        user = User(
            username=username,
            hashed_password=hash_password(password),
            role=Role.ADMIN,
        )
        await self.users.add(user)
