"""User repository (auth)."""
from __future__ import annotations

from sqlalchemy import select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return await self.session.scalar(stmt)
