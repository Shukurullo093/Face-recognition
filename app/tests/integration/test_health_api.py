"""Liveness/readiness over the real ASGI stack (no DB, no models)."""
from __future__ import annotations


async def test_health_ok(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


async def test_ready_reports_components(client):
    # ASGITransport skips lifespan, so the DB ping fails -> degraded, but the
    # endpoint must still answer 200 with a per-component breakdown.
    resp = await client.get("/api/v1/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"ok", "degraded"}
    assert set(body) >= {"database", "models_loaded"}
