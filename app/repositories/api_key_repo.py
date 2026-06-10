"""API key repository."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update

from app.models.api_key import ApiKey
from app.repositories.base import BaseRepository


class ApiKeyRepository(BaseRepository[ApiKey]):
    model = ApiKey

    async def get_active_by_hash(self, key_hash: str) -> ApiKey | None:
        stmt = select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
        return await self.session.scalar(stmt)

    async def list_all(self) -> list[ApiKey]:
        stmt = select(ApiKey).order_by(ApiKey.created_at.desc())
        return list((await self.session.scalars(stmt)).all())

    async def touch(self, key_id, when: datetime) -> None:
        """Best-effort last_used_at update (own transaction, never blocks search)."""
        await self.session.execute(
            update(ApiKey).where(ApiKey.id == key_id).values(last_used_at=when)
        )
