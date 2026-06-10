"""Person repository."""
from __future__ import annotations

from sqlalchemy import func, select

from app.models.person import Person
from app.repositories.base import BaseRepository


class PersonRepository(BaseRepository[Person]):
    model = Person

    async def count(self) -> int:
        return await self.session.scalar(select(func.count()).select_from(Person)) or 0

    async def get_by_external_id(self, external_id: str) -> Person | None:
        stmt = select(Person).where(Person.external_id == external_id)
        return await self.session.scalar(stmt)

    async def get_by_name(self, full_name: str) -> Person | None:
        stmt = select(Person).where(Person.full_name == full_name).limit(1)
        return await self.session.scalar(stmt)
