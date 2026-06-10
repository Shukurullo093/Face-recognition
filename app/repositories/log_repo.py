"""Recognition audit-log repository."""
from __future__ import annotations

from sqlalchemy import func, select

from app.models.recognition_log import RecognitionLog
from app.repositories.base import BaseRepository


class RecognitionLogRepository(BaseRepository[RecognitionLog]):
    model = RecognitionLog

    async def record(self, **fields: object) -> RecognitionLog:
        entry = RecognitionLog(**fields)  # type: ignore[arg-type]
        return await self.add(entry)

    async def recent(self, limit: int = 50) -> list[RecognitionLog]:
        stmt = select(RecognitionLog).order_by(RecognitionLog.created_at.desc()).limit(limit)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def count(self) -> int:
        return await self.session.scalar(select(func.count()).select_from(RecognitionLog)) or 0

    async def success_count(self) -> int:
        stmt = select(func.count()).select_from(RecognitionLog).where(
            RecognitionLog.success.is_(True)
        )
        return await self.session.scalar(stmt) or 0
