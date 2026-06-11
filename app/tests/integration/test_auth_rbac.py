"""Auth + RBAC gating. These run without a DB: the role check happens in a
dependency before any repository/DB access, so a minted JWT is enough."""
from __future__ import annotations

import uuid

from app.core.security import Role


async def test_protected_endpoint_requires_token(client):
    resp = await client.get("/api/v1/persons")
    assert resp.status_code == 401


async def test_malformed_token_rejected(client):
    resp = await client.get(
        "/api/v1/persons", headers={"Authorization": "Bearer not.a.real.jwt"}
    )
    assert resp.status_code == 401


async def test_admin_only_endpoint_forbids_viewer(client, auth_headers):
    # Import-status requires admin; a viewer token must be rejected before the
    # handler (and any store/DB access) runs.
    resp = await client.get(
        f"/api/v1/faces/import/{uuid.uuid4()}", headers=auth_headers(Role.VIEWER)
    )
    assert resp.status_code == 403


async def test_admin_only_endpoint_forbids_operator(client, auth_headers):
    resp = await client.get(
        f"/api/v1/faces/import/{uuid.uuid4()}", headers=auth_headers(Role.OPERATOR)
    )
    assert resp.status_code == 403


async def test_admin_passes_rbac_then_404_for_unknown_job(client, auth_headers):
    # Admin clears RBAC; the unknown job id resolves via the in-process job store
    # (no DB) -> 404. Confirms gating lets admins through to the handler.
    resp = await client.get(
        f"/api/v1/faces/import/{uuid.uuid4()}", headers=auth_headers(Role.ADMIN)
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"
