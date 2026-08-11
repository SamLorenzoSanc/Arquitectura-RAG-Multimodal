"""Utilidades GeoJSON para parcelas (polígono + centroide + área aproximada)."""

from __future__ import annotations

import json
import math
from typing import Any, Optional


def normalize_polygon(poligono: Any) -> Optional[dict[str, Any]]:
    """Acepta GeoJSON Polygon o anillo [[lat,lon],...] / [[lon,lat],...] y normaliza."""
    if poligono is None:
        return None
    if isinstance(poligono, str):
        try:
            poligono = json.loads(poligono)
        except json.JSONDecodeError:
            return None

    if isinstance(poligono, dict) and poligono.get("type") == "Polygon":
        coords = poligono.get("coordinates")
        if not coords or not coords[0] or len(coords[0]) < 4:
            return None
        ring = list(coords[0])
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        return {"type": "Polygon", "coordinates": [ring]}

    if isinstance(poligono, list) and len(poligono) >= 3:
        # Heurística: si |x|<=90 y |y|>90 → lat,lon; si no, asumimos lon,lat si |x|>|lat típica|
        first = poligono[0]
        if not isinstance(first, (list, tuple)) or len(first) < 2:
            return None
        a, b = float(first[0]), float(first[1])
        # UI Leaflet suele mandar [lat, lon]
        as_latlon = abs(a) <= 90 and abs(b) <= 180
        ring = []
        for pt in poligono:
            if as_latlon:
                lat, lon = float(pt[0]), float(pt[1])
                ring.append([lon, lat])
            else:
                ring.append([float(pt[0]), float(pt[1])])
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        return {"type": "Polygon", "coordinates": [ring]}

    return None


def polygon_centroid(poligono: dict[str, Any] | None) -> Optional[tuple[float, float]]:
    """Devuelve (lat, lon) centroide del anillo exterior."""
    if not poligono:
        return None
    ring = poligono.get("coordinates", [[]])[0]
    if len(ring) < 3:
        return None
    pts = ring[:-1] if ring[0] == ring[-1] else ring
    if not pts:
        return None
    lon = sum(float(p[0]) for p in pts) / len(pts)
    lat = sum(float(p[1]) for p in pts) / len(pts)
    return (lat, lon)


def polygon_area_ha(poligono: dict[str, Any] | None) -> Optional[float]:
    """Área aproximada (ha) con fórmula del shoelace sobre proyección equirectangular."""
    if not poligono:
        return None
    ring = poligono.get("coordinates", [[]])[0]
    pts = ring[:-1] if ring and ring[0] == ring[-1] else ring
    if not pts or len(pts) < 3:
        return None
    lat0 = sum(float(p[1]) for p in pts) / len(pts)
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(lat0))
    xy = [
        (float(p[0]) * m_per_deg_lon, float(p[1]) * m_per_deg_lat) for p in pts
    ]
    area = 0.0
    for i in range(len(xy)):
        x1, y1 = xy[i]
        x2, y2 = xy[(i + 1) % len(xy)]
        area += x1 * y2 - x2 * y1
    area_m2 = abs(area) / 2.0
    return round(area_m2 / 10_000.0, 4)


def polygon_vertex_count(poligono: dict[str, Any] | None) -> int:
    if not poligono:
        return 0
    ring = poligono.get("coordinates", [[]])[0]
    if not ring:
        return 0
    n = len(ring)
    if n >= 2 and ring[0] == ring[-1]:
        return n - 1
    return n


def dumps_polygon(poligono: dict[str, Any] | None) -> Optional[str]:
    if poligono is None:
        return None
    return json.dumps(poligono)
