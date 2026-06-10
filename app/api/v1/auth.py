"""Auth endpoints: token issuance + user management (admin only)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import AuthServiceDep, require_admin
from app.schemas.auth import Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=Token, summary="OAuth2 password login")
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth: AuthServiceDep,
) -> Token:
    return await auth.authenticate(form.username, form.password)


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    summary="Create a user (admin only)",
)
async def create_user(payload: UserCreate, auth: AuthServiceDep) -> UserRead:
    user = await auth.create_user(payload)
    return UserRead(
        id=str(user.id), username=user.username, role=user.role, is_active=user.is_active
    )
