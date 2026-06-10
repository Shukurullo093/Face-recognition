"""Aggregate v1 router."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import analytics, api_keys, auth, external, faces, health, persons

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(persons.router)
api_router.include_router(faces.router)
api_router.include_router(analytics.router)
api_router.include_router(api_keys.router)
api_router.include_router(external.router)
