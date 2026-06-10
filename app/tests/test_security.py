"""JWT, password hashing and RBAC tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import AuthenticationError
from app.core.security import (
    Role,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_roundtrip() -> None:
    token = create_access_token(subject="alice", role=Role.OPERATOR)
    payload = decode_access_token(token)
    assert payload["sub"] == "alice"
    assert payload["role"] == "operator"


def test_decode_invalid_token_raises() -> None:
    with pytest.raises(AuthenticationError):
        decode_access_token("garbage.token.value")


@pytest.mark.parametrize(
    ("role", "required", "ok"),
    [
        (Role.ADMIN, Role.VIEWER, True),
        (Role.ADMIN, Role.OPERATOR, True),
        (Role.OPERATOR, Role.ADMIN, False),
        (Role.VIEWER, Role.OPERATOR, False),
        (Role.VIEWER, Role.VIEWER, True),
    ],
)
def test_role_hierarchy(role: Role, required: Role, ok: bool) -> None:
    assert role.satisfies(required) is ok
