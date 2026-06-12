"""FastAPI application entrypoint.

Lifespan loads the heavy ONNX models exactly once and stores the pipeline on
app.state, so every request reuses warm GPU sessions (no per-request model load).
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import limiter
from app.db.session import AsyncSessionFactory
from app.recognition.pipeline import RecognitionPipeline
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log.info("startup_begin", env=settings.ENVIRONMENT)

    # Load ONNX models once (skippable in unit tests via FR_SKIP_MODELS=1).
    if os.getenv("FR_SKIP_MODELS") == "1":
        app.state.pipeline = None
        log.warning("models_skipped", reason="FR_SKIP_MODELS=1")
    else:
        app.state.pipeline = RecognitionPipeline.from_settings(settings)
        log.info("models_loaded")
        # Absorb first-inference JIT/warmup cost at startup, not on the first request.
        app.state.pipeline.warmup()

    # Bootstrap a first admin in non-production if configured.
    bootstrap_user = os.getenv("BOOTSTRAP_ADMIN_USER")
    bootstrap_pass = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
    if bootstrap_user and bootstrap_pass:
        async with AsyncSessionFactory() as session:
            await AuthService(UserRepository(session), settings).ensure_bootstrap_admin(
                bootstrap_user, bootstrap_pass
            )
            await session.commit()
        log.info("bootstrap_admin_ready", user=bootstrap_user)

    log.info("startup_complete")
    yield
    log.info("shutdown_complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        default_response_class=ORJSONResponse,
        docs_url="/docs",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        lifespan=lifespan,
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(
        RateLimitExceeded,
        lambda request, exc: ORJSONResponse(
            status_code=429,
            content={"error": {"code": "rate_limited", "message": "Too many requests"}},
        ),
    )

    # CORS (tighten origins per deployment)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Static dashboard SPA at /dashboard (served only if the directory exists).
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    if frontend_dir.is_dir():
        app.mount(
            "/dashboard",
            StaticFiles(directory=str(frontend_dir), html=True),
            name="dashboard",
        )
        log.info("dashboard_mounted", path="/dashboard")

    return app


app = create_app()
