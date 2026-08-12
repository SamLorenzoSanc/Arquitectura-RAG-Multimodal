from pydantic import BaseModel, Field


class PointModel(BaseModel):
    row: int = Field(..., ge=0)
    col: int = Field(..., ge=0)


class RecogidaRequest(BaseModel):
    grid: list[list[int]] = Field(
        ...,
        description="Rejilla: 0 libre, 1 obstáculo, 2 fruta (transitable)",
    )
    start: PointModel
    fruits: list[PointModel] = Field(default_factory=list)
    return_to_start: bool = True


class RecogidaResponse(BaseModel):
    found: bool
    order: list[list[int]]
    full_path: list[list[int]]
    segments: list[dict]
    total_cost: float
    nodes_expanded: int
    return_to_start: bool
    stops: int | None = None
    path_length: int | None = None
    failed_segment: dict | None = None


class GeoPoint(BaseModel):
    lat: float
    lon: float


class GeoRutaRequest(BaseModel):
    start: GeoPoint = Field(description="Cooperativa / posición del camión")
    stops: list[GeoPoint] = Field(
        default_factory=list,
        description="Puntos de recogida de fruta",
    )
    return_to_start: bool = True
    max_snap_m: float = Field(
        default=800.0,
        description="Distancia máxima para acoplar un punto a la carretera",
    )
