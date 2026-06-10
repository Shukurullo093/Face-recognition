"""Person CRUD endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DBDep, require_operator, require_viewer
from app.core.exceptions import EntityConflictError, EntityNotFoundError
from app.models.person import Person
from app.repositories.person_repo import PersonRepository
from app.schemas.person import PersonCreate, PersonRead

router = APIRouter(prefix="/persons", tags=["persons"])


@router.post(
    "",
    response_model=PersonRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_operator)],
    summary="Create a person",
)
async def create_person(payload: PersonCreate, db: DBDep) -> Person:
    repo = PersonRepository(db)
    if payload.external_id and await repo.get_by_external_id(payload.external_id):
        raise EntityConflictError(f"external_id '{payload.external_id}' already exists")
    return await repo.add(
        Person(
            full_name=payload.full_name,
            external_id=payload.external_id,
            meta=payload.metadata,
        )
    )


@router.get(
    "",
    response_model=list[PersonRead],
    dependencies=[Depends(require_viewer)],
    summary="List persons",
)
async def list_persons(
    db: DBDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Person]:
    return await PersonRepository(db).list(limit=limit, offset=offset)


@router.get(
    "/{person_id}",
    response_model=PersonRead,
    dependencies=[Depends(require_viewer)],
    summary="Get a person",
)
async def get_person(person_id: uuid.UUID, db: DBDep) -> Person:
    person = await PersonRepository(db).get(person_id)
    if person is None:
        raise EntityNotFoundError(f"Person {person_id} not found")
    return person
