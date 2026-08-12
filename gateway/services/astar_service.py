"""Algoritmo A* para rutas de recogida de fruta en parcela."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from typing import Iterable


Point = tuple[int, int]


@dataclass(frozen=True)
class AStarResult:
    path: list[Point]
    cost: float
    nodes_expanded: int
    found: bool


def heuristic(a: Point, b: Point) -> float:
    """Distancia octile (admite movimiento en 8 direcciones)."""
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return (dx + dy) + (math.sqrt(2) - 2) * min(dx, dy)


def neighbors(p: Point, rows: int, cols: int) -> Iterable[tuple[Point, float]]:
    r, c = p
    deltas = [
        (-1, 0, 1.0),
        (1, 0, 1.0),
        (0, -1, 1.0),
        (0, 1, 1.0),
        (-1, -1, math.sqrt(2)),
        (-1, 1, math.sqrt(2)),
        (1, -1, math.sqrt(2)),
        (1, 1, math.sqrt(2)),
    ]
    for dr, dc, cost in deltas:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            yield (nr, nc), cost


def astar(
    grid: list[list[int]],
    start: Point,
    goal: Point,
    *,
    obstacle_value: int = 1,
) -> AStarResult:
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    if rows == 0 or cols == 0:
        return AStarResult([], float("inf"), 0, False)

    def walkable(cell: Point) -> bool:
        r, c = cell
        return grid[r][c] != obstacle_value

    if not walkable(start) or not walkable(goal):
        return AStarResult([], float("inf"), 0, False)

    open_heap: list[tuple[float, float, Point]] = []
    heapq.heappush(open_heap, (heuristic(start, goal), 0.0, start))
    came_from: dict[Point, Point] = {}
    g_score: dict[Point, float] = {start: 0.0}
    closed: set[Point] = set()
    expanded = 0

    while open_heap:
        _, g, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        closed.add(current)
        expanded += 1

        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return AStarResult(path, g_score[goal], expanded, True)

        for nxt, step_cost in neighbors(current, rows, cols):
            if not walkable(nxt) or nxt in closed:
                continue
            tentative = g + step_cost
            if tentative < g_score.get(nxt, float("inf")):
                came_from[nxt] = current
                g_score[nxt] = tentative
                f = tentative + heuristic(nxt, goal)
                heapq.heappush(open_heap, (f, tentative, nxt))

    return AStarResult([], float("inf"), expanded, False)


def nearest_neighbor_order(start: Point, points: list[Point]) -> list[Point]:
    remaining = points[:]
    order: list[Point] = []
    current = start
    while remaining:
        nxt = min(remaining, key=lambda p: heuristic(current, p))
        remaining.remove(nxt)
        order.append(nxt)
        current = nxt
    return order


def plan_fruit_collection(
    grid: list[list[int]],
    start: Point,
    fruits: list[Point],
    *,
    return_to_start: bool = True,
    obstacle_value: int = 1,
) -> dict:
    unique_fruits = []
    seen: set[Point] = set()
    for f in fruits:
        p = (int(f[0]), int(f[1]))
        if p not in seen:
            seen.add(p)
            unique_fruits.append(p)

    if not unique_fruits:
        return {
            "found": True,
            "order": [],
            "full_path": [list(start)],
            "segments": [],
            "total_cost": 0.0,
            "nodes_expanded": 0,
            "return_to_start": return_to_start,
        }

    order = nearest_neighbor_order(start, unique_fruits)
    waypoints = [start] + order
    if return_to_start:
        waypoints.append(start)

    full_path: list[Point] = []
    segments = []
    total_cost = 0.0
    total_expanded = 0

    for i in range(len(waypoints) - 1):
        a, b = waypoints[i], waypoints[i + 1]
        result = astar(grid, a, b, obstacle_value=obstacle_value)
        total_expanded += result.nodes_expanded
        if not result.found:
            return {
                "found": False,
                "order": [list(p) for p in order],
                "full_path": [list(p) for p in full_path],
                "segments": segments,
                "total_cost": total_cost,
                "nodes_expanded": total_expanded,
                "return_to_start": return_to_start,
                "failed_segment": {"from": list(a), "to": list(b)},
            }

        segment_path = result.path if not full_path else result.path[1:]
        full_path.extend(segment_path)
        total_cost += result.cost
        segments.append(
            {
                "from": list(a),
                "to": list(b),
                "path": [list(p) for p in result.path],
                "cost": round(result.cost, 3),
                "nodes_expanded": result.nodes_expanded,
            }
        )

    return {
        "found": True,
        "order": [list(p) for p in order],
        "full_path": [list(p) for p in full_path],
        "segments": segments,
        "total_cost": round(total_cost, 3),
        "nodes_expanded": total_expanded,
        "return_to_start": return_to_start,
        "stops": len(order),
        "path_length": max(0, len(full_path) - 1),
    }


def demo_banana_parcel(rows: int = 12, cols: int = 16) -> dict:
    grid = [[0 for _ in range(cols)] for _ in range(rows)]

    for r in range(4, 7):
        for c in range(7, 10):
            grid[r][c] = 1
    for r in range(1, 3):
        for c in range(12, 15):
            grid[r][c] = 1
    for r in range(8, 11):
        grid[r][4] = 1

    fruits = [
        (1, 2),
        (2, 5),
        (3, 11),
        (5, 2),
        (6, 13),
        (8, 8),
        (9, 1),
        (10, 12),
        (11, 6),
    ]
    for r, c in fruits:
        grid[r][c] = 2

    start = (0, 0)
    return {
        "rows": rows,
        "cols": cols,
        "grid": grid,
        "start": list(start),
        "fruits": [list(p) for p in fruits],
        "legend": {
            "0": "pasillo / suelo transitable",
            "1": "obstáculo (riego, almacén, valla)",
            "2": "punto de recogida de fruta",
        },
        "description": (
            "Parcela demo de plátano (La Palma). "
            "A* calcula la ruta más eficiente visitando todos los racimos."
        ),
    }
