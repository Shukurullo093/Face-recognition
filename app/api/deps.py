"""FastAPI dependencies: DB session, current user, RBAC, service factories.

This module is the Composition Root — it wires concrete repositories and the
shared ML pipeline into services via DI, so business code stays decoupled.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings, settings as _settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    RateLimitExceededError,
)
from app.core.rate_limit import external_rate_limiter, parse_rate
from app.core.security import Role, decode_access_token, hash_api_key
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.recognition.pipeline import RecognitionPipeline
from app.repositories.api_key_repo import ApiKeyRepository
from app.repositories.face_repo import FaceRepository
from app.repositories.log_repo import RecognitionLogRepository
from app.repositories.person_repo import PersonRepository
from app.repositories.user_repo import UserRepository
from app.schemas.auth import TokenPayload
from app.services.api_key_service import ApiKeyService
from app.services.auth_service import AuthService
from app.services.bulk_import_service import BulkImportService
from app.services.recognition_service import RecognitionService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{get_settings().API_V1_PREFIX}/auth/token")

SettingsDep = Annotated[Settings, Depends(get_settings)]
DBDep = Annotated[AsyncSession, Depends(get_db)]


# ---------- shared singletons ----------
def get_pipeline(request: Request) -> RecognitionPipeline:
    """The heavy ML pipeline, built once in the lifespan handler."""
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:  # pragma: no cover - defensive
        raise RuntimeError("Recognition pipeline not initialised")
    return pipeline


PipelineDep = Annotated[RecognitionPipeline, Depends(get_pipeline)]


# ---------- auth ----------
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> TokenPayload:
    payload = decode_access_token(token)
    sub = payload.get("sub")
    role = payload.get("role")
    if not sub or not role:
        raise AuthenticationError("Malformed token payload")
    return TokenPayload(sub=sub, role=Role(role))


CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]


def require_role(minimum: Role) -> Callable[[TokenPayload], TokenPayload]:
    """Dependency factory enforcing a minimum RBAC level."""

    async def _checker(user: CurrentUser) -> TokenPayload:
        if not user.role.satisfies(minimum):
            raise AuthorizationError(
                f"Requires '{minimum.value}' role or higher (you have '{user.role.value}')"
            )
        return user

    return _checker


require_viewer = require_role(Role.VIEWER)
require_operator = require_role(Role.OPERATOR)
require_admin = require_role(Role.ADMIN)


# ---------- service factories (DI) ----------
def get_auth_service(db: DBDep, settings: SettingsDep) -> AuthService:
    return AuthService(UserRepository(db), settings)


def get_recognition_service(
    request: Request,
    db: DBDep,
    settings: SettingsDep,
    pipeline: PipelineDep,
    user: CurrentUser,
) -> RecognitionService:
    return RecognitionService(
        pipeline=pipeline,
        person_repo=PersonRepository(db),
        face_repo=FaceRepository(db, ef_search=settings.HNSW_EF_SEARCH),
        log_repo=RecognitionLogRepository(db),
        settings=settings,
        actor=user.sub,
        client_ip=request.client.host if request.client else None,
    )


def get_bulk_import_service(settings: SettingsDep, pipeline: PipelineDep) -> BulkImportService:
    return BulkImportService(pipeline=pipeline, settings=settings)


def get_api_key_service(db: DBDep) -> ApiKeyService:
    return ApiKeyService(ApiKeyRepository(db))


# ---------- API-key (3rd-party) auth ----------
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(
    db: DBDep, key: Annotated[str | None, Security(_api_key_header)]
) -> ApiKey:
    if not key:
        raise AuthenticationError("Missing X-API-Key header")
    repo = ApiKeyRepository(db)
    entity = await repo.get_active_by_hash(hash_api_key(key))
    if entity is None:
        raise AuthenticationError("Invalid or revoked API key")
    limit, window = parse_rate(_settings.EXTERNAL_RATE_LIMIT)
    if not external_rate_limiter.allow(str(entity.id), limit, window):
        raise RateLimitExceededError(f"API key rate limit exceeded ({_settings.EXTERNAL_RATE_LIMIT})")
    await repo.touch(entity.id, datetime.now(UTC))  # committed by get_db
    return entity


def get_external_recognition_service(
    request: Request,
    db: DBDep,
    settings: SettingsDep,
    pipeline: PipelineDep,
    api_key: Annotated[ApiKey, Depends(get_api_key)],
) -> RecognitionService:
    return RecognitionService(
        pipeline=pipeline,
        person_repo=PersonRepository(db),
        face_repo=FaceRepository(db, ef_search=settings.HNSW_EF_SEARCH),
        log_repo=RecognitionLogRepository(db),
        settings=settings,
        actor=f"apikey:{api_key.name}",
        client_ip=request.client.host if request.client else None,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
RecognitionServiceDep = Annotated[RecognitionService, Depends(get_recognition_service)]
BulkImportServiceDep = Annotated[BulkImportService, Depends(get_bulk_import_service)]
ApiKeyServiceDep = Annotated[ApiKeyService, Depends(get_api_key_service)]
ExternalRecognitionServiceDep = Annotated[
    RecognitionService, Depends(get_external_recognition_service)
]
