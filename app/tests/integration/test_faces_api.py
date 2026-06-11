"""Faces enroll / verify / 1:N search over the real DB. Skipped unless
RUN_DB_TESTS=1.

These also need a working recognition pipeline. Either run with real models
(unset FR_SKIP_MODELS and provide ONNX models) or override `get_pipeline` with a
fake that returns deterministic embeddings (see app/tests/conftest.py fakes).

Template — fill in once a model/fake strategy is chosen:
"""
from __future__ import annotations

import io

import pytest

from app.core.security import Role

pytestmark = pytest.mark.dbtest


def _png_bytes() -> bytes:
    """Minimal in-memory PNG so multipart upload validation passes."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (160, 160), (128, 128, 128)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.skip(reason="needs a recognition pipeline (real models or a fake) wired in")
async def test_enroll_then_search(db_client, auth_headers):
    files = {"image": ("face.png", _png_bytes(), "image/png")}
    data = {"person_name": "Search Target"}
    resp = await db_client.post(
        "/api/v1/faces/enroll",
        data=data,
        files=files,
        headers=auth_headers(Role.OPERATOR),
    )
    assert resp.status_code == 201

    resp = await db_client.post(
        "/api/v1/faces/search",
        files={"image": ("query.png", _png_bytes(), "image/png")},
        headers=auth_headers(Role.VIEWER),
    )
    assert resp.status_code == 200
    assert "matches" in resp.json()
