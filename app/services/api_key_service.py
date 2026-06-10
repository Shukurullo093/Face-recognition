"""API key management service."""
from __future__ import annotations

import uuid

from app.core.exceptions import EntityNotFoundError
from app.core.security import generate_api_key
from app.models.api_key import ApiKey
from app.repositories.api_key_repo import ApiKeyRepository
from app.schemas.api_key import ApiKeyCreated


class ApiKeyService:
    def __init__(self, repo: ApiKeyRepository) -> None:
        self.repo = repo

    async def create(self, name: str, created_by: str | None) -> ApiKeyCreated:
        raw, key_hash, prefix = generate_api_key()
        entity = await self.repo.add(
            ApiKey(name=name, key_hash=key_hash, prefix=prefix, created_by=created_by)
        )
        return ApiKeyCreated(
            id=entity.id,
            name=entity.name,
            prefix=entity.prefix,
            is_active=entity.is_active,
            created_by=entity.created_by,
            last_used_at=entity.last_used_at,
            created_at=entity.created_at,
            key=raw,
        )

    async def list(self) -> list[ApiKey]:
        return await self.repo.list_all()

    async def revoke(self, key_id: uuid.UUID) -> None:
        entity = await self.repo.get(key_id)
        if entity is None:
            raise EntityNotFoundError(f"API key {key_id} not found")
        await self.repo.delete(entity)
