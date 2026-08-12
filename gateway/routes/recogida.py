from fastapi import APIRouter, Depends, HTTPException, Query

from routes.auth import get_current_user
from models.user import User
from schemas.recogida import (
    GeoRutaRequest,
    RecogidaRequest,
    RecogidaResponse,
)
from services.astar_service import demo_banana_parcel, plan_fruit_collection
from services.geo_astar_service import (
    get_la_palma_graph,
    map_context,
    plan_geo_collection,
)

router = APIRouter(prefix="/recogida", tags=["Recogida"])


@router.get("/demo")
async def get_demo_scenario(current_user: User = Depends(get_current_user)):
    """Escenario de parcela de plátano (rejilla) listo para planificar con A*."""
    return demo_banana_parcel()


@router.post("/ruta", response_model=RecogidaResponse)
async def calcular_ruta_recogida(
    request: RecogidaRequest,
    current_user: User = Depends(get_current_user),
):
    """Calcula la ruta de recogida de fruta con A* en rejilla."""
    if not request.grid or not request.grid[0]:
        raise HTTPException(status_code=400, detail="La rejilla no puede estar vacía")

    rows = len(request.grid)
    cols = len(request.grid[0])
    if any(len(row) != cols for row in request.grid):
        raise HTTPException(
            status_code=400, detail="Todas las filas deben tener la misma longitud"
        )

    start = (request.start.row, request.start.col)
    if not (0 <= start[0] < rows and 0 <= start[1] < cols):
        raise HTTPException(
            status_code=400, detail="El punto de inicio está fuera de la rejilla"
        )

    fruits = []
    for f in request.fruits:
        p = (f.row, f.col)
        if not (0 <= p[0] < rows and 0 <= p[1] < cols):
            raise HTTPException(
                status_code=400,
                detail=f"Punto de fruta fuera de rejilla: {p}",
            )
        fruits.append(p)

    if not fruits:
        for r, row in enumerate(request.grid):
            for c, val in enumerate(row):
                if val == 2:
                    fruits.append((r, c))

    return plan_fruit_collection(
        request.grid,
        start,
        fruits,
        return_to_start=request.return_to_start,
    )


@router.get("/mapa")
async def get_mapa_la_palma(
    refresh: bool = Query(False),
    current_user: User = Depends(get_current_user),
):
    """Mapa de La Palma + red viaria para A* geográfico."""
    if refresh:
        await get_la_palma_graph(force_refresh=True)
    return await map_context()


@router.post("/mapa/ruta")
async def calcular_ruta_geografica(
    request: GeoRutaRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Ruta de recogida en La Palma con A* sobre carreteras.

    El camión solo puede circular por la red viaria; fuera de carretera = obstáculo.
    """
    if not request.stops:
        raise HTTPException(
            status_code=400,
            detail="Añade al menos un punto de recogida en el mapa",
        )

    graph = await get_la_palma_graph()
    result = plan_geo_collection(
        graph,
        (request.start.lat, request.start.lon),
        [(s.lat, s.lon) for s in request.stops],
        return_to_start=request.return_to_start,
        max_snap_m=request.max_snap_m,
    )
    if not result.get("found"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error") or "No se pudo calcular la ruta por carretera",
        )
    return result
