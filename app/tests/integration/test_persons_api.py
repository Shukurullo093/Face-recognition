"""Persons CRUD over the real DB. Skipped unless RUN_DB_TESTS=1.

Template for full request→DB→response coverage. Extend with pagination,
external_id conflict (409), update (PATCH), and cascade-delete-of-faces cases.
"""
from __future__ import annotations

import uuid

import pytest

from app.core.security import Role

pytestmark = pytest.mark.dbtest


async def test_person_create_get_delete(db_client, auth_headers):
    # create (operator+)
    resp = await db_client.post(
        "/api/v1/persons",
        json={"full_name": "Integration Tester"},
        headers=auth_headers(Role.OPERATOR),
    )
    assert resp.status_code == 201
    person_id = resp.json()["id"]

    # read (viewer+)
    resp = await db_client.get(
        f"/api/v1/persons/{person_id}", headers=auth_headers(Role.VIEWER)
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Integration Tester"

    # delete (operator+)
    resp = await db_client.delete(
        f"/api/v1/persons/{person_id}", headers=auth_headers(Role.OPERATOR)
    )
    assert resp.status_code == 204

    # gone
    resp = await db_client.get(
        f"/api/v1/persons/{person_id}", headers=auth_headers(Role.VIEWER)
    )
    assert resp.status_code == 404


async def test_get_unknown_person_404(db_client, auth_headers):
    resp = await db_client.get(
        f"/api/v1/persons/{uuid.uuid4()}", headers=auth_headers(Role.VIEWER)
    )
    assert resp.status_code == 404
