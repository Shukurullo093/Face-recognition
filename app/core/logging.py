"""Structured logging setup using structlog. Console (dev) or JSON (prod)."""
from __future__ import annotations

import logging
import sys

import structlog

from app.core.config import settings


def configure_logging() -> None:
    """Configure stdlib logging + structlog once at startup."""
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.LOG_JSON:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Tame noisy third-party loggers
    logging.basicConfig(level=level, format="%(message)s", stream=sys.stderr)
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
