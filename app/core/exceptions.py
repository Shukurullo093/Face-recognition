"""Domain exceptions + FastAPI exception handlers.

Keeping domain errors HTTP-agnostic respects Clean Architecture: services raise
domain errors, the API layer maps them to HTTP responses.
"""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import ORJSONResponse

from app.core.logging import get_logger

log = get_logger(__name__)


class DomainError(Exception):
    """Base class for all expected, recoverable domain errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "domain_error"

    def __init__(self, message: str, *, detail: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}


class NoFaceDetectedError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "no_face_detected"


class MultipleFacesError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "multiple_faces"


class InvalidImageError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "invalid_image"


class LowQualityFaceError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "low_quality_face"


class EntityNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class EntityConflictError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class AuthenticationError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentication_error"


class AuthorizationError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "authorization_error"


class RateLimitExceededError(DomainError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limited"


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers that translate domain errors -> JSON responses."""

    @app.exception_handler(DomainError)
    async def _domain_handler(request: Request, exc: DomainError) -> ORJSONResponse:
        log.warning(
            "domain_error",
            code=exc.code,
            message=exc.message,
            path=request.url.path,
        )
        return ORJSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "detail": exc.detail}},
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception) -> ORJSONResponse:
        log.error("unhandled_error", error=str(exc), path=request.url.path, exc_info=exc)
        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": "internal_error", "message": "Internal server error"}},
        )
