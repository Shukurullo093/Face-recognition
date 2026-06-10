"""Read-only analytics endpoints powering the dashboard (stats + audit logs)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DBDep, require_viewer
from app.repositories.face_repo import FaceRepository
from app.repositories.log_repo import RecognitionLogRepository
from app.repositories.person_repo import PersonRepository
from app.schemas.analytics import LogRead, StatsResponse

router = APIRouter(tags=["analytics"], dependencies=[Depends(require_viewer)])


@router.get("/stats", response_model=StatsResponse, summary="Aggregate system stats")
async def get_stats(db: DBDep) -> StatsResponse:
    persons = await PersonRepository(db).count()
    faces = await FaceRepository(db).count()
    log_repo = RecognitionLogRepository(db)
    total_events = await log_repo.count()
    successful = await log_repo.success_count()
    return StatsResponse(
        total_persons=persons,
        total_faces=faces,
        total_events=total_events,
        successful_events=successful,
        match_rate=round(successful / total_events, 4) if total_events else 0.0,
    )


@router.get("/logs", response_model=list[LogRead], summary="Recent recognition events")
async def get_logs(
    db: DBDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list:
    return await RecognitionLogRepository(db).recent(limit=limit)
