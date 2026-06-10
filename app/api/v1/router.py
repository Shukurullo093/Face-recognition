"""Aggregate v1 router."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import analytics, auth, faces, health, persons

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(persons.router)
api_router.include_router(faces.router)
api_router.include_router(analytics.router)
