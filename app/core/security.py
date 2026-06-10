"""JWT creation/validation + password hashing + RBAC role enum."""
from __future__ import annotations

import enum
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import AuthenticationError

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# bcrypt only considers the first 72 bytes of the input; longer inputs raise on
# bcrypt>=4. Truncating keeps behaviour well-defined and avoids 500s on input.
_BCRYPT_MAX_BYTES = 72


def _truncate(secret: str) -> bytes:
    return secret.encode("utf-8")[:_BCRYPT_MAX_BYTES]


class Role(str, enum.Enum):
    """RBAC roles, ordered by privilege (admin > operator > viewer)."""

    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"

    @property
    def level(self) -> int:
        return {Role.VIEWER: 1, Role.OPERATOR: 2, Role.ADMIN: 3}[self]

    def satisfies(self, required: "Role") -> bool:
        """True if this role meets or exceeds the required privilege level."""
        return self.level >= required.level


def hash_password(plain: str) -> str:
    return _pwd_context.hash(_truncate(plain))


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(_truncate(plain), hashed)


def create_access_token(subject: str, role: Role, expires_minutes: int | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {"sub": subject, "role": role.value, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc


# ---- API keys (machine-to-machine) ----
API_KEY_PREFIX = "frk_"


def generate_api_key() -> tuple[str, str, str]:
    """Return (raw_key, sha256_hash, display_prefix).

    The raw key is shown to the caller exactly once; only the hash is stored.
    """
    raw = API_KEY_PREFIX + secrets.token_urlsafe(32)
    return raw, hash_api_key(raw), raw[:12]


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
