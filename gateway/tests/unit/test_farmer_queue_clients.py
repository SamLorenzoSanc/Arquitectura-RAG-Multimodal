"""Tests unitarios del mapeo de perfil agricultor."""

from __future__ import annotations

import pytest

from services.farmer_context_service import (
    format_parcel_markdown,
    map_crop_to_product_id,
    map_island_to_code,
)

pytestmark = pytest.mark.unit


def test_map_crop_and_island():
    assert map_crop_to_product_id("Plátano Canarias") == "platano_canarias"
    assert map_crop_to_product_id("Tomate Daniela") == "tomate"
    assert map_crop_to_product_id(None) == "platano_canarias"
    assert map_island_to_code("La Palma") == "La_Palma"
    assert map_island_to_code(None) == "La_Palma"


def test_format_parcel_markdown_includes_cultivo():
    md = format_parcel_markdown(
        {
            "id": "c1",
            "nombre": "Finca Demo",
            "cultivo": "Plátano",
            "isla": "La Palma",
            "lat": 28.68,
            "lon": -17.76,
            "sistema_riego": "Goteo",
        },
        treatments=[
            {
                "producto": "Oillette",
                "fecha": "2026-03-12",
                "carencia_dias": 3,
            }
        ],
    )
    assert "Finca Demo" in md
    assert "Plátano" in md
    assert "Oillette" in md
