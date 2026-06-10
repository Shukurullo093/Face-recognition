"""API smoke test for the health endpoint (no DB / model required)."""
from __future__ import annotations

import os

os.environ["FR_SKIP_MODELS"] = "1"
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_at_least_32_characters_long")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_health_ok() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["version"] == "1.0.0"


def test_search_requires_auth() -> None:
    with TestClient(app) as client:
        resp = client.post("/api/v1/faces/search", files={"image": ("x.jpg", b"data")})
        assert resp.status_code == 401
