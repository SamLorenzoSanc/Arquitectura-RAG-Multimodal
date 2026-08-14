"""Tests del servicio de importación opendata con sesión mock."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from services import opendata_service

pytestmark = pytest.mark.unit

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "opendata" / "sat_sample.csv"


@pytest.mark.asyncio
async def test_import_sat_file_executes_upserts():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    result = await opendata_service.import_sat_file(db, FIXTURE)

    assert result["imported"] >= 3
    assert result["source_file"].endswith("sat_sample.csv")
    assert db.execute.await_count >= result["imported"]
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_import_opendata_directory_missing():
    db = AsyncMock()
    with pytest.raises(FileNotFoundError):
        await opendata_service.import_opendata_directory(
            db, directory="/ruta/inexistente-opendata"
        )


@pytest.mark.asyncio
async def test_list_sat_societies_applies_filters():
    db = AsyncMock()
    mapping_row = MagicMock()
    mapping_row.__iter__ = lambda self: iter(())
    result = MagicMock()
    result.mappings.return_value.all.return_value = [
        {
            "denominacion": "SAT Norte",
            "situacion": "Activa",
            "direccion_municipio_nombre": "La Laguna",
            "objeto_social_principal_nombre": "Producción Agrícola",
        },
        {
            "denominacion": "SAT Sur",
            "situacion": "Cancelada",
            "direccion_municipio_nombre": "Arona",
            "objeto_social_principal_nombre": "Comercio",
        },
    ]
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()

    rows = await opendata_service.list_sat_societies(
        db, municipio="laguna", situacion="activa"
    )
    assert len(rows) == 1
    assert rows[0]["denominacion"] == "SAT Norte"
