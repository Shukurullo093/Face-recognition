"""Integration-test harness for the HTTP API.

Two tiers of tests live under this directory:

* **No-DB tests** (run by default): liveness + auth/RBAC gating. They drive the
  ASGI app through httpx with no external services — RBAC is enforced in a
  dependency *before* the DB is touched, so a minted JWT is all that's needed.
* **DB tests** (`@pytest.mark.dbtest`): full request→DB→response flows. Skipped
  unless ``RUN_DB_TESTS=1`` and ``TEST_DATABASE_URL`` point at a migrated
  Postgres+pgvector instance.

httpx's ASGITransport does not run lifespan events, so we set
``app.state.pipeline`` and override ``get_pipeline`` here instead of loading the
real ONNX models.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Settings must validate without a real .env, and models must not load.
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_at_least_32_characters_long")
os.environ.setdefault("FR_SKIP_MODELS", "1")

from app.api.deps import get_pipeline  # noqa: E402
from app.core.security import Role, create_access_token  # noqa: E402
from app.main import create_app  # noqa: E402


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "dbtest: needs a real Postgres+pgvector; runs only with RUN_DB_TESTS=1",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if os.getenv("RUN_DB_TESTS") == "1":
        return
    skip_db = pytest.mark.skip(
        reason="DB test — set RUN_DB_TESTS=1 and TEST_DATABASE_URL to run"
    )
    for item in items:
        if item.get_closest_marker("dbtest"):
            item.add_marker(skip_db)


class _StubPipeline:
    """Stand-in so get_pipeline doesn't raise. ML paths are exercised by @dbtest."""


@pytest.fixture
def app():
    application = create_app()
    application.state.pipeline = _StubPipeline()
    application.dependency_overrides[get_pipeline] = lambda: application.state.pipeline
    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app):
    """Unauthenticated client. Add headers per request via `auth_headers`."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
def auth_headers():
    """Factory: `auth_headers(Role.OPERATOR)` -> Authorization header for that role.

    Tokens are minted directly (no login round-trip), so RBAC can be tested
    without seeding a user in the DB — `get_current_user` only decodes the JWT.
    """

    def _make(role: Role = Role.ADMIN, subject: str = "tester") -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(subject, role)}"}

    return _make


@pytest_asyncio.fixture
async def db_client(app):
    """Authenticated-capable client wired to a real test DB (DB tests only).

    Requires ``TEST_DATABASE_URL`` (async DSN, e.g.
    ``postgresql+asyncpg://face:face_password@localhost:5432/facedb_test``) and a
    schema already created via ``alembic upgrade head`` against that database.
    """
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    from app.db.session import get_db

    url = os.environ["TEST_DATABASE_URL"]
    engine = create_async_engine(url, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    await engine.dispose()
