"""Tests unitarios de geometría de parcelas (GeoJSON)."""

from __future__ import annotations

import pytest

from services.geo_polygon import (
    normalize_polygon,
    polygon_area_ha,
    polygon_centroid,
    polygon_vertex_count,
)

pytestmark = pytest.mark.unit


def test_normalize_polygon_geojson_closes_ring():
    poly = {
        "type": "Polygon",
        "coordinates": [
            [
                [-17.7650, 28.6825],
                [-17.7634, 28.6825],
                [-17.7634, 28.6845],
                [-17.7650, 28.6845],
            ]
        ],
    }
    out = normalize_polygon(poly)
    assert out is not None
    ring = out["coordinates"][0]
    assert ring[0] == ring[-1]
    assert polygon_vertex_count(out) == 4


def test_normalize_polygon_from_latlon_list():
    pts = [
        [28.6825, -17.7650],
        [28.6825, -17.7634],
        [28.6845, -17.7634],
        [28.6845, -17.7650],
    ]
    out = normalize_polygon(pts)
    assert out["type"] == "Polygon"
    lat, lon = polygon_centroid(out)
    assert 28.68 < lat < 28.69
    assert -17.77 < lon < -17.76


def test_normalize_rejects_invalid():
    assert normalize_polygon(None) is None
    assert normalize_polygon("not-json") is None
    assert normalize_polygon({"type": "Point"}) is None
    assert polygon_area_ha(None) is None
    assert polygon_centroid(None) is None
    assert polygon_vertex_count(None) == 0


def test_polygon_area_positive():
    poly = normalize_polygon(
        {
            "type": "Polygon",
            "coordinates": [
                [
                    [-17.7650, 28.6825],
                    [-17.7634, 28.6825],
                    [-17.7634, 28.6845],
                    [-17.7650, 28.6845],
                    [-17.7650, 28.6825],
                ]
            ],
        }
    )
    area = polygon_area_ha(poly)
    assert area is not None and area > 0
