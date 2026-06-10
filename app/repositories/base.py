"""Generic async repository base (Repository Pattern)."""
from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """CRUD primitives shared by all repositories.

    Repositories never commit — the unit-of-work boundary lives in the
    `get_db` dependency, so a request's writes commit/rollback atomically.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def list(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()  # assign PK / defaults without committing
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()
