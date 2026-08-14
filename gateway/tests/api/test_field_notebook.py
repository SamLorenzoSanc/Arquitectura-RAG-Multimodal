"""Tests API del cuaderno de campo."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.api


def _mappings_result(rows: list[dict]):
    result = MagicMock()
    result.mappings.return_value.all.return_value = rows
    result.mappings.return_value.first.return_value = rows[0] if rows else None
    result.rowcount = len(rows)
    return result


def test_list_requires_auth(client):
    response = client.get("/api/v1/field-notebook/")
    assert response.status_code in (401, 403, 422)


def test_list_entries(authenticated_client, override_db):
    override_db.execute = AsyncMock(
        return_value=_mappings_result(
            [
                {
                    "id": "n1",
                    "user_id": "user-123",
                    "organization_id": None,
                    "crop_id": None,
                    "entry_date": date(2026, 8, 13),
                    "title": "Riego de la parcela norte",
                    "body": "Goteros revisados",
                    "category": "riego",
                    "reminder_at": None,
                    "created_at": None,
                    "updated_at": None,
                }
            ]
        )
    )
    with patch(
        "routes.field_notebook.init_field_notebook_table", new=AsyncMock()
    ):
        response = authenticated_client.get("/api/v1/field-notebook/")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["data"][0]["title"] == "Riego de la parcela norte"


def test_create_entry(authenticated_client, override_db):
    created = {
        "id": "n2",
        "user_id": "user-123",
        "organization_id": None,
        "crop_id": None,
        "entry_date": date(2026, 8, 13),
        "title": "Manchas en hoja",
        "body": "Revisar trips",
        "category": "plaga",
        "reminder_at": None,
        "created_at": None,
        "updated_at": None,
    }
    insert_result = MagicMock()
    insert_result.rowcount = 1
    select_result = _mappings_result([created])
    override_db.execute = AsyncMock(side_effect=[insert_result, select_result])
    override_db.commit = AsyncMock()

    with patch(
        "routes.field_notebook.init_field_notebook_table", new=AsyncMock()
    ):
        response = authenticated_client.post(
            "/api/v1/field-notebook/",
            json={
                "title": "Manchas en hoja",
                "body": "Revisar trips",
                "entry_date": "2026-08-13",
                "category": "plaga",
            },
        )
    assert response.status_code == 201
    assert response.json()["data"]["category"] == "plaga"
    override_db.commit.assert_awaited()


def test_delete_missing_entry(authenticated_client, override_db):
    missing = MagicMock()
    missing.rowcount = 0
    override_db.execute = AsyncMock(return_value=missing)
    override_db.rollback = AsyncMock()
    with patch(
        "routes.field_notebook.init_field_notebook_table", new=AsyncMock()
    ):
        response = authenticated_client.delete("/api/v1/field-notebook/no-existe")
    assert response.status_code == 404
