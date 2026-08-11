"""A* geográfico sobre red viaria (OpenStreetMap) de La Palma.

Solo se puede circular por carreteras: salirse de la vía no es un nodo del grafo
y por tanto actúa como obstáculo implícito.
"""

from __future__ import annotations

import heapq
import json
import math
import time
from pathlib import Path
from typing import Any

import httpx

# Bbox aproximado de La Palma (sur, oeste, norte, este)
LA_PALMA_BBOX = (28.43, -18.02, 28.88, -17.68)

# Cooperativa / zona logística por defecto (Los Llanos – área agrícola)
DEFAULT_COOPERATIVA = {
    "name": "Cooperativa (punto de camión)",
    "lat": 28.6585,
    "lon": -17.9085,
}

CACHE_DIR = Path(__file__).resolve().parent / "geo_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
ROADS_CACHE = CACHE_DIR / "la_palma_roads.json"

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _quantize(lat: float, lon: float, decimals: int = 5) -> tuple[float, float]:
    return (round(lat, decimals), round(lon, decimals))


def _fallback_roads() -> list[list[list[float]]]:
    """
    Red viaria de respaldo densificada (oeste / zona agrícola de La Palma).

    Se usa cuando Overpass no responde. Incluye corredores cerca de Los Llanos,
    Tazacorte y fincas del oeste para que las paradas típicas acoplen a < 200 m.
    """
    return [
        # LP-2 / corredor Santa Cruz → Los Llanos
        [
            [28.6839, -17.7644],
            [28.6780, -17.7900],
            [28.6720, -17.8200],
            [28.6660, -17.8600],
            [28.6610, -17.8850],
            [28.6585, -17.9085],
        ],
        # Los Llanos → costa oeste (Tazacorte / Puerto)
        [
            [28.6585, -17.9085],
            [28.6550, -17.9200],
            [28.6500, -17.9300],
            [28.6460, -17.9383],
            [28.6420, -17.9480],
            [28.6380, -17.9580],
            [28.6350, -17.9680],
        ],
        # Anillo agrícola oeste (cubre paradas del usuario)
        [
            [28.6460, -17.9383],
            [28.6520, -17.9360],
            [28.6580, -17.9345],
            [28.6624, -17.9339],
            [28.6680, -17.9380],
            [28.6737, -17.9459],
            [28.6780, -17.9520],
            [28.6800, -17.9600],
        ],
        # Conexión cooperativa ↔ anillo oeste
        [
            [28.6585, -17.9085],
            [28.6600, -17.9180],
            [28.6624, -17.9339],
        ],
        [
            [28.6585, -17.9085],
            [28.6650, -17.9200],
            [28.6737, -17.9459],
        ],
        [
            [28.6585, -17.9085],
            [28.6520, -17.9220],
            [28.6460, -17.9383],
        ],
        # Norte (Tijarafe / Puntagorda)
        [
            [28.6624, -17.9339],
            [28.6800, -17.9350],
            [28.7000, -17.9380],
            [28.7200, -17.9420],
            [28.7400, -17.9450],
            [28.7600, -17.9400],
        ],
        # Sur (Fuencaliente / zona platanera)
        [
            [28.6460, -17.9383],
            [28.6300, -17.9300],
            [28.6100, -17.9200],
            [28.5800, -17.9000],
            [28.5500, -17.8850],
            [28.5200, -17.8750],
            [28.4900, -17.8500],
        ],
        # Este costa
        [
            [28.6839, -17.7644],
            [28.6600, -17.7700],
            [28.6300, -17.7800],
            [28.6000, -17.7900],
            [28.5600, -17.8000],
        ],
        # Ramal interior El Paso
        [
            [28.6585, -17.9085],
            [28.6520, -17.8900],
            [28.6460, -17.8700],
            [28.6400, -17.8500],
        ],
        # Malla local densificada alrededor de las fincas oeste
        [
            [28.6460, -17.9383],
            [28.6490, -17.9420],
            [28.6520, -17.9460],
            [28.6560, -17.9480],
            [28.6600, -17.9470],
            [28.6650, -17.9460],
            [28.6700, -17.9460],
            [28.6737, -17.9459],
        ],
        [
            [28.6624, -17.9339],
            [28.6620, -17.9400],
            [28.6610, -17.9450],
            [28.6600, -17.9500],
            [28.6580, -17.9550],
        ],
    ]


class RoadGraph:
    def __init__(self):
        self.nodes: dict[int, tuple[float, float]] = {}
        self.adj: dict[int, list[tuple[int, float]]] = {}
        self.road_polylines: list[list[list[float]]] = []
        self.source: str = "empty"

    def add_edge(self, a: int, b: int, cost: float):
        self.adj.setdefault(a, []).append((b, cost))
        self.adj.setdefault(b, []).append((a, cost))

    def nearest_node(self, lat: float, lon: float) -> tuple[int, float]:
        best_id = -1
        best_d = float("inf")
        for nid, (nlat, nlon) in self.nodes.items():
            d = haversine_m(lat, lon, nlat, nlon)
            if d < best_d:
                best_d = d
                best_id = nid
        return best_id, best_d

    def astar(self, start_id: int, goal_id: int) -> dict[str, Any]:
        if start_id not in self.nodes or goal_id not in self.nodes:
            return {"found": False, "path": [], "cost_m": float("inf"), "expanded": 0}

        goal_lat, goal_lon = self.nodes[goal_id]

        def h(nid: int) -> float:
            lat, lon = self.nodes[nid]
            return haversine_m(lat, lon, goal_lat, goal_lon)

        open_heap: list[tuple[float, float, int]] = []
        heapq.heappush(open_heap, (h(start_id), 0.0, start_id))
        came_from: dict[int, int] = {}
        g_score: dict[int, float] = {start_id: 0.0}
        closed: set[int] = set()
        expanded = 0

        while open_heap:
            _, g, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            closed.add(current)
            expanded += 1

            if current == goal_id:
                path_ids = [current]
                while current in came_from:
                    current = came_from[current]
                    path_ids.append(current)
                path_ids.reverse()
                coords = [list(self.nodes[i]) for i in path_ids]
                return {
                    "found": True,
                    "path": coords,
                    "cost_m": round(g_score[goal_id], 1),
                    "expanded": expanded,
                    "node_ids": path_ids,
                }

            for nxt, step in self.adj.get(current, []):
                if nxt in closed:
                    continue
                tentative = g + step
                if tentative < g_score.get(nxt, float("inf")):
                    came_from[nxt] = current
                    g_score[nxt] = tentative
                    heapq.heappush(open_heap, (tentative + h(nxt), tentative, nxt))

        return {"found": False, "path": [], "cost_m": float("inf"), "expanded": expanded}


def _build_graph_from_polylines(
    polylines: list[list[list[float]]],
    *,
    step_m: float = 80.0,
) -> RoadGraph:
    """Construye grafo muestreando puntos a lo largo de cada carretera."""
    graph = RoadGraph()
    key_to_id: dict[tuple[float, float], int] = {}
    next_id = 0

    def get_id(lat: float, lon: float) -> int:
        nonlocal next_id
        key = _quantize(lat, lon)
        if key in key_to_id:
            return key_to_id[key]
        nid = next_id
        next_id += 1
        key_to_id[key] = nid
        graph.nodes[nid] = key
        return nid

    for line in polylines:
        if len(line) < 2:
            continue
        # Densificar / muestrear
        sampled: list[list[float]] = [line[0]]
        acc = 0.0
        for i in range(1, len(line)):
            lat0, lon0 = sampled[-1]
            lat1, lon1 = line[i]
            seg = haversine_m(lat0, lon0, lat1, lon1)
            if seg < 1e-3:
                continue
            if acc + seg < step_m and i < len(line) - 1:
                acc += seg
                continue
            # interpolar si el segmento es muy largo
            if seg > step_m * 1.5:
                n = max(2, int(seg // step_m))
                for k in range(1, n + 1):
                    t = k / n
                    sampled.append(
                        [
                            lat0 + (lat1 - lat0) * t,
                            lon0 + (lon1 - lon0) * t,
                        ]
                    )
            else:
                sampled.append([lat1, lon1])
            acc = 0.0

        graph.road_polylines.append(sampled)
        ids = [get_id(p[0], p[1]) for p in sampled]
        for a, b in zip(ids, ids[1:]):
            if a == b:
                continue
            la, loa = graph.nodes[a]
            lb, lob = graph.nodes[b]
            cost = haversine_m(la, loa, lb, lob)
            graph.add_edge(a, b, cost)

    # Conectar nodos cercanos (cruces) con rejilla espacial
    cell = 0.00035  # ~35–40 m
    buckets: dict[tuple[int, int], list[int]] = {}
    for nid, (lat, lon) in graph.nodes.items():
        key = (int(lat / cell), int(lon / cell))
        buckets.setdefault(key, []).append(nid)

    join_threshold = 45.0
    for (ci, cj), ids in buckets.items():
        candidates = list(ids)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                candidates.extend(buckets.get((ci + di, cj + dj), []))
        for i, ida in enumerate(ids):
            lata, lona = graph.nodes[ida]
            for idb in candidates:
                if idb <= ida:
                    continue
                latb, lonb = graph.nodes[idb]
                d = haversine_m(lata, lona, latb, lonb)
                if 0 < d <= join_threshold:
                    graph.add_edge(ida, idb, d)

    return graph


def _parse_overpass(data: dict) -> list[list[list[float]]]:
    nodes = {
        el["id"]: (el["lat"], el["lon"])
        for el in data.get("elements", [])
        if el.get("type") == "node" and "lat" in el and "lon" in el
    }
    polylines: list[list[list[float]]] = []
    for el in data.get("elements", []):
        if el.get("type") != "way":
            continue
        coords = []
        for nid in el.get("nodes", []):
            if nid in nodes:
                lat, lon = nodes[nid]
                coords.append([lat, lon])
        if len(coords) >= 2:
            polylines.append(coords)
    return polylines


async def fetch_la_palma_roads(*, force_refresh: bool = False) -> list[list[list[float]]]:
    if ROADS_CACHE.exists() and not force_refresh:
        age_h = (time.time() - ROADS_CACHE.stat().st_mtime) / 3600
        if age_h < 24 * 14:  # cache 2 semanas
            cached = json.loads(ROADS_CACHE.read_text(encoding="utf-8"))
            if cached.get("polylines"):
                return cached["polylines"]

    south, west, north, east = LA_PALMA_BBOX
    # Consulta más ligera: menos tipos = menos timeouts en Overpass
    query = f"""
    [out:json][timeout:60];
    (
      way["highway"~"^(primary|secondary|tertiary|unclassified|residential)$"]({south},{west},{north},{east});
    );
    out body;
    >;
    out skel qt;
    """

    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=70.0) as client:
        for url in OVERPASS_URLS:
            try:
                resp = await client.post(url, data={"data": query})
                resp.raise_for_status()
                polylines = _parse_overpass(resp.json())
                if len(polylines) < 5:
                    raise RuntimeError("Respuesta Overpass demasiado pequeña")
                # Mezclar con fallback para no perder cobertura agrícola oeste
                merged = list(polylines) + _fallback_roads()
                ROADS_CACHE.write_text(
                    json.dumps({"polylines": merged, "ts": time.time()}),
                    encoding="utf-8",
                )
                return merged
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue

    print(f"[GEO-ASTAR] Overpass falló ({last_error}); usando red simplificada")
    return _fallback_roads()


_GRAPH: RoadGraph | None = None
_GRAPH_SOURCE = ""


async def get_la_palma_graph(*, force_refresh: bool = False) -> RoadGraph:
    global _GRAPH, _GRAPH_SOURCE
    if _GRAPH is not None and not force_refresh:
        return _GRAPH

    polylines = await fetch_la_palma_roads(force_refresh=force_refresh)
    source = "osm+fallback" if ROADS_CACHE.exists() and len(polylines) > 30 else "fallback"
    if len(polylines) <= len(_fallback_roads()) + 2:
        source = "fallback"

    graph = _build_graph_from_polylines(
        polylines, step_m=70.0 if source.startswith("osm") else 90.0
    )
    graph.source = source
    _GRAPH = graph
    _GRAPH_SOURCE = source
    return graph


def plan_geo_collection(
    graph: RoadGraph,
    start: tuple[float, float],
    stops: list[tuple[float, float]],
    *,
    return_to_start: bool = True,
    max_snap_m: float = 800.0,
) -> dict[str, Any]:
    start_id, start_snap = graph.nearest_node(start[0], start[1])
    if start_id < 0 or start_snap > max_snap_m:
        return {
            "found": False,
            "error": (
                f"El punto de la cooperativa está a {start_snap:.0f} m de la carretera "
                f"(máx. {max_snap_m:.0f} m). Sitúalo más cerca de una vía."
            ),
            "snap_m": start_snap,
        }

    stop_nodes: list[tuple[int, float, tuple[float, float]]] = []
    for lat, lon in stops:
        nid, dist = graph.nearest_node(lat, lon)
        if nid < 0 or dist > max_snap_m:
            return {
                "found": False,
                "error": (
                    f"La parada ({lat:.4f}, {lon:.4f}) está a {dist:.0f} m de la red viaria "
                    f"(máx. {max_snap_m:.0f} m). Acércala a una carretera gris del mapa "
                    f"o aumenta el margen de acoplado."
                ),
                "snap_m": dist,
            }
        stop_nodes.append((nid, dist, (lat, lon)))

    # Orden nearest-neighbor sobre nodos
    remaining = stop_nodes[:]
    order: list[tuple[int, float, tuple[float, float]]] = []
    current = start_id
    while remaining:
        best_i = 0
        best_d = float("inf")
        clat, clon = graph.nodes[current]
        for i, (nid, _, _) in enumerate(remaining):
            nlat, nlon = graph.nodes[nid]
            d = haversine_m(clat, clon, nlat, nlon)
            if d < best_d:
                best_d = d
                best_i = i
        chosen = remaining.pop(best_i)
        order.append(chosen)
        current = chosen[0]

    waypoints = [start_id] + [o[0] for o in order]
    if return_to_start:
        waypoints.append(start_id)

    full_path: list[list[float]] = []
    segments = []
    total = 0.0
    expanded = 0

    for a, b in zip(waypoints, waypoints[1:]):
        result = graph.astar(a, b)
        expanded += result["expanded"]
        if not result["found"]:
            return {
                "found": False,
                "error": (
                    "No hay camino por carretera entre dos paradas (red desconectada). "
                    "A* solo puede circular por aristas de la red viaria cargada: "
                    "si dos puntos caen en componentes separados (p. ej. red de respaldo incompleta "
                    "o paradas muy alejadas sin enlace), no existe ruta válida. "
                    "Prueba acercar las paradas a la misma carretera gris continua "
                    "o reiniciar el mapa para recargar la red."
                ),
                "order": [[*p[2]] for p in order],
                "full_path": full_path,
                "total_cost_m": total,
                "nodes_expanded": expanded,
            }
        path = result["path"]
        if full_path and path:
            path = path[1:]
        full_path.extend(path)
        total += result["cost_m"]
        segments.append(
            {
                "from": list(graph.nodes[a]),
                "to": list(graph.nodes[b]),
                "path": result["path"],
                "cost_m": result["cost_m"],
                "nodes_expanded": result["expanded"],
            }
        )

    start_snapped = list(graph.nodes[start_id])
    return {
        "found": True,
        "start_snapped": start_snapped,
        "start_snap_m": round(start_snap, 1),
        "order": [[*p[2]] for p in order],
        "order_snapped": [list(graph.nodes[p[0]]) for p in order],
        "full_path": full_path,
        "segments": segments,
        "total_cost_m": round(total, 1),
        "total_cost_km": round(total / 1000.0, 2),
        "nodes_expanded": expanded,
        "return_to_start": return_to_start,
        "stops": len(order),
        "graph_source": graph.source,
        "message": (
            "Ruta calculada solo por carreteras. "
            "Salirse de la vía no está permitido (obstáculo)."
        ),
    }


async def map_context() -> dict[str, Any]:
    graph = await get_la_palma_graph()
    # Limitar polylines enviadas al front para no saturar
    roads = graph.road_polylines
    if len(roads) > 800:
        roads = roads[:: max(1, len(roads) // 800)]
    return {
        "bbox": {
            "south": LA_PALMA_BBOX[0],
            "west": LA_PALMA_BBOX[1],
            "north": LA_PALMA_BBOX[2],
            "east": LA_PALMA_BBOX[3],
        },
        "center": {"lat": 28.66, "lon": -17.86},
        "cooperativa": DEFAULT_COOPERATIVA,
        "roads": roads,
        "nodes": len(graph.nodes),
        "source": graph.source,
        "description": (
            "Mapa de La Palma: el camión parte de la cooperativa y solo puede "
            "circular por carreteras OSM. Fuera de la red viaria es obstáculo."
        ),
    }
