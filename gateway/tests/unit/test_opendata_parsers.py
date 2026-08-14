"""Tests unitarios de parsers de datos abiertos Canarias."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.opendata_parsers import (
    filter_sat_rows,
    normalize_sat_row,
    parse_istac_sheet_rows,
    parse_sat_csv,
    series_id_from_filename,
)

pytestmark = pytest.mark.unit

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "opendata" / "sat_sample.csv"


def test_normalize_sat_row_ok():
    row = normalize_sat_row(
        {
            "denominacion": "Cooperativa Demo",
            "nif": "V12345678",
            "numero_socios": "12",
            "situacion": "Activa",
            "direccion_municipio_nombre": "Los Llanos de Aridane",
            "objeto_social_principal_nombre": "Producción Agrícola",
        }
    )
    assert row is not None
    assert row["denominacion"] == "Cooperativa Demo"
    assert row["numero_socios"] == 12


def test_normalize_sat_row_rejects_empty_name():
    assert normalize_sat_row({"denominacion": "  ", "nif": "V1"}) is None


def test_normalize_sat_unknown_nif():
    row = normalize_sat_row({"denominacion": "SAT X", "nif": "_U"})
    assert row is not None
    assert row["nif"] is None


def test_parse_sat_csv_fixture():
    rows = parse_sat_csv(FIXTURE)
    assert len(rows) >= 3
    assert all(r["denominacion"] for r in rows)


def test_filter_sat_rows_by_municipio_and_cnae():
    rows = [
        {
            "denominacion": "A",
            "situacion": "Activa",
            "direccion_municipio_nombre": "Santa Cruz de Tenerife",
            "objeto_social_principal_nombre": "Producción Agrícola",
        },
        {
            "denominacion": "B",
            "situacion": "Cancelada",
            "direccion_municipio_nombre": "Los Llanos de Aridane",
            "objeto_social_principal_nombre": "Ganadería",
        },
    ]
    filtered = filter_sat_rows(rows, municipio="tenerife", cnae_contains="agrícola")
    assert len(filtered) == 1
    assert filtered[0]["denominacion"] == "A"


def test_series_id_from_filename():
    assert (
        series_id_from_filename("dataset-ISTAC-C00038D_000001-~latest-selection.xlsx")
        == "dataset-ISTAC-C00038D_000001"
    )


def test_parse_istac_sheet_rows_extracts_numbers():
    sheet = [
        ["Exportación de plátanos", None, None],
        [None, None, None],
        ["Última actualización", "24-jul-2026", None],
        [None, "2020", "2021"],
        ["Tenerife", "1000", "1100,5"],
        ["Gran Canaria", "800", "no-num"],
    ]
    parsed = parse_istac_sheet_rows(
        sheet, series_id="demo", source_file="demo.xlsx"
    )
    assert parsed["title"].startswith("Exportación")
    assert parsed["updated_at"] == "24-jul-2026"
    assert len(parsed["observations"]) == 3
    values = {(o["row_label"], o["column_label"], o["value"]) for o in parsed["observations"]}
    assert ("Tenerife", "2020", 1000.0) in values
    assert ("Tenerife", "2021", 1100.5) in values
