"""Tests API de datos abiertos Canarias."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from main import app
from routes.opendata import require_admin


pytestmark = pytest.mark.api


def test_get_sat_requires_auth(client):
    response = client.get("/api/v1/opendata/sat")
    assert response.status_code in (401, 403, 422)


def test_get_sat_authenticated(authenticated_client):
    with patch(
        "opendata.adapters.inbound.http.opendata_service.list_sat_societies",
        new=AsyncMock(return_value=[{"denominacion": "SAT Demo"}]),
    ):
        response = authenticated_client.get("/api/v1/opendata/sat?municipio=Tenerife")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["data"][0]["denominacion"] == "SAT Demo"


def test_import_requires_admin(authenticated_client):
    with patch("opendata.adapters.inbound.http.user_is_admin", new=AsyncMock(return_value=False)):
        response = authenticated_client.post("/api/v1/opendata/import")
    assert response.status_code == 403


def test_import_as_admin(authenticated_client):
    app.dependency_overrides[require_admin] = lambda: MagicUser()
    try:
        with patch(
            "opendata.adapters.inbound.http.opendata_service.import_opendata_directory",
            new=AsyncMock(
                return_value={
                    "directory": "data/opendata",
                    "sat_files": 1,
                    "istac_files": 2,
                    "sat": [],
                    "istac": [],
                }
            ),
        ):
            response = authenticated_client.post("/api/v1/opendata/import")
        assert response.status_code == 200
        assert response.json()["sat_files"] == 1
    finally:
        app.dependency_overrides.pop(require_admin, None)


def test_istac_series_and_observations(authenticated_client):
    with patch(
        "opendata.adapters.inbound.http.opendata_service.list_istac_series",
        new=AsyncMock(return_value=[{"series_id": "s1", "title": "Plátanos"}]),
    ):
        series = authenticated_client.get("/api/v1/opendata/istac/series")
    assert series.status_code == 200
    assert series.json()["data"][0]["series_id"] == "s1"

    with patch(
        "opendata.adapters.inbound.http.opendata_service.list_istac_observations",
        new=AsyncMock(return_value=[{"row_label": "Tenerife", "value": 10.0}]),
    ):
        obs = authenticated_client.get(
            "/api/v1/opendata/istac/series/s1/observations"
        )
    assert obs.status_code == 200
    assert obs.json()["count"] == 1


class MagicUser:
    id = "admin-1"
    email = "admin@example.com"
