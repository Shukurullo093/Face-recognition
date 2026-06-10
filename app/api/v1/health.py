"""Health & readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import text

from app.api.deps import DBDep
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME, "version": "1.0.0"}


@router.get("/ready", summary="Readiness probe (DB + models)")
async def ready(request: Request, db: DBDep) -> dict[str, object]:
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False
    models_ok = getattr(request.app.state, "pipeline", None) is not None
    return {
        "status": "ok" if (db_ok and models_ok) else "degraded",
        "database": db_ok,
        "models_loaded": models_ok,
    }
