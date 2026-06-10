"""API key management (admin only)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import ApiKeyServiceDep, require_admin
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyRead

router = APIRouter(prefix="/api-keys", tags=["api-keys"], dependencies=[Depends(require_admin)])


@router.post(
    "",
    response_model=ApiKeyCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Create an API key (raw key returned once)",
)
async def create_key(payload: ApiKeyCreate, service: ApiKeyServiceDep, request_user=Depends(require_admin)) -> ApiKeyCreated:
    return await service.create(payload.name, created_by=request_user.sub)


@router.get("", response_model=list[ApiKeyRead], summary="List API keys (masked)")
async def list_keys(service: ApiKeyServiceDep) -> list:
    return await service.list()


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    summary="Revoke (delete) an API key",
)
async def revoke_key(key_id: uuid.UUID, service: ApiKeyServiceDep) -> None:
    await service.revoke(key_id)
