from datetime import date
from typing import Any, List, Optional, Union
from uuid import uuid4
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db
from services.geo_polygon import (
    dumps_polygon,
    normalize_polygon,
    polygon_area_ha,
    polygon_centroid,
)
from .auth import get_current_user

router = APIRouter(prefix="/crops", tags=["Crops"])


class TreatmentCreateSchema(BaseModel):
    fecha: date
    producto: str
    materia_activa: Optional[str] = None
    dosis: Optional[str] = None
    plaga_objetivo: Optional[str] = None
    carencia_dias: Optional[int] = None
    observaciones: Optional[str] = None


class CropCreateSchema(BaseModel):
    nombre: str
    cultivo: str
    isla: str
    lat: float
    lon: float
    temperatura: float = 22.0
    humedad: float = 65.0
    lluvia: float = 0.0
    viento: float = 12.0
    ndvi: float = 0.7
    sentinel_tile: Optional[str] = None
    organization_id: Optional[str] = None
    ref_catastral: Optional[str] = None
    superficie_ha: Optional[float] = None
    variedad: Optional[str] = None
    sistema_riego: Optional[str] = None
    fuente_agua: Optional[str] = None
    dotacion_m3_ha_anio: Optional[float] = None
    comunidad_regantes: Optional[str] = None
    certificaciones: Optional[str] = None
    notas: Optional[str] = None
    parcela_codigo: Optional[str] = None
    # GeoJSON Polygon o anillo [[lat,lon],...]
    poligono: Optional[Any] = None


class CropUpdateSchema(BaseModel):
    nombre: Optional[str] = None
    cultivo: Optional[str] = None
    isla: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    temperatura: Optional[float] = None
    humedad: Optional[float] = None
    lluvia: Optional[float] = None
    viento: Optional[float] = None
    ndvi: Optional[float] = None
    sentinel_tile: Optional[str] = None
    organization_id: Optional[str] = None
    ref_catastral: Optional[str] = None
    superficie_ha: Optional[float] = None
    variedad: Optional[str] = None
    sistema_riego: Optional[str] = None
    fuente_agua: Optional[str] = None
    dotacion_m3_ha_anio: Optional[float] = None
    comunidad_regantes: Optional[str] = None
    certificaciones: Optional[str] = None
    notas: Optional[str] = None
    parcela_codigo: Optional[str] = None
    poligono: Optional[Any] = None


CROP_COLUMNS = """
    id, user_id, organization_id, nombre, cultivo, isla, lat, lon,
    temperatura, humedad, lluvia, viento, ndvi, sentinel_tile,
    ref_catastral, superficie_ha, variedad, sistema_riego,
    fuente_agua, dotacion_m3_ha_anio, comunidad_regantes,
    certificaciones, notas, parcela_codigo, poligono
"""


def _prepare_crop_payload(raw: dict[str, Any]) -> dict[str, Any]:
    payload = dict(raw)
    poly = normalize_polygon(payload.pop("poligono", None))
    payload["poligono"] = dumps_polygon(poly)
    if poly:
        centroid = polygon_centroid(poly)
        if centroid and (
            payload.get("lat") is None
            or payload.get("lon") is None
            or (payload.get("lat") == 0 and payload.get("lon") == 0)
        ):
            payload["lat"], payload["lon"] = centroid
        elif centroid and "lat" in payload and "lon" in payload:
            # Si hay polígono, el centroide es la ubicación canónica
            payload["lat"], payload["lon"] = centroid
        if payload.get("superficie_ha") is None:
            area = polygon_area_ha(poly)
            if area is not None:
                payload["superficie_ha"] = area
    return payload


def _serialize_crop(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    if out.get("organization_id") is not None:
        out["organization_id"] = str(out["organization_id"])
    if out.get("fecha") is not None:
        out["fecha"] = str(out["fecha"])
    poly = out.get("poligono")
    if isinstance(poly, str):
        try:
            out["poligono"] = json.loads(poly)
        except json.JSONDecodeError:
            out["poligono"] = None
    return out


@router.post("/", status_code=201)
async def create_crop(
    data: Union[CropCreateSchema, List[CropCreateSchema]],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = str(current_user.id)
    items = data if isinstance(data, list) else [data]
    created_ids: list[str] = []

    query = text(
        """
        INSERT INTO crops (
            id, user_id, organization_id, nombre, cultivo, isla, lat, lon,
            temperatura, humedad, lluvia, viento, ndvi, sentinel_tile,
            ref_catastral, superficie_ha, variedad, sistema_riego,
            fuente_agua, dotacion_m3_ha_anio, comunidad_regantes,
            certificaciones, notas, parcela_codigo, poligono
        ) VALUES (
            :id, :user_id, :organization_id, :nombre, :cultivo, :isla, :lat, :lon,
            :temperatura, :humedad, :lluvia, :viento, :ndvi, :sentinel_tile,
            :ref_catastral, :superficie_ha, :variedad, :sistema_riego,
            :fuente_agua, :dotacion_m3_ha_anio, :comunidad_regantes,
            :certificaciones, :notas, :parcela_codigo, CAST(:poligono AS jsonb)
        )
        """
    )

    try:
        for crop in items:
            crop_id = str(uuid4())
            payload = _prepare_crop_payload(crop.model_dump())
            await db.execute(
                query,
                {"id": crop_id, "user_id": user_id, **payload},
            )
            created_ids.append(crop_id)

        await db.commit()
        return {
            "ids": created_ids,
            "status": "success",
            "message": f"Se ha(n) creado {len(created_ids)} parcela(s) correctamente",
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al guardar el cultivo: {str(e)}"
        )


@router.get("/", status_code=200)
async def get_user_crops(
    organization_id: Optional[str] = Query(None),
    include_treatments: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = str(current_user.id)
    try:
        params: dict[str, Any] = {"user_id": user_id}
        org_sql = ""
        if organization_id:
            org_sql = " AND (organization_id = :organization_id OR organization_id IS NULL)"
            params["organization_id"] = organization_id

        result = await db.execute(
            text(
                f"""
                SELECT {CROP_COLUMNS}
                FROM crops
                WHERE user_id = :user_id{org_sql}
                ORDER BY nombre
                """
            ),
            params,
        )
        crops = [_serialize_crop(dict(r)) for r in result.mappings().all()]

        if include_treatments and crops:
            from sqlalchemy import bindparam

            ids = [c["id"] for c in crops]
            t_query = text(
                """
                SELECT id, crop_id, fecha, producto, materia_activa, dosis,
                       plaga_objetivo, carencia_dias, observaciones, created_at
                FROM crop_treatments
                WHERE crop_id IN :ids
                ORDER BY fecha DESC
                """
            ).bindparams(bindparam("ids", expanding=True))
            t_result = await db.execute(t_query, {"ids": ids})
            by_crop: dict[str, list] = {i: [] for i in ids}
            for row in t_result.mappings().all():
                item = dict(row)
                item["fecha"] = str(item["fecha"]) if item.get("fecha") else None
                if item.get("created_at"):
                    item["created_at"] = str(item["created_at"])
                by_crop.setdefault(item["crop_id"], []).append(item)
            for crop in crops:
                crop["treatments"] = by_crop.get(crop["id"], [])

        return {"status": "success", "data": crops}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener los cultivos: {str(e)}"
        )


@router.get("/{crop_id}", status_code=200)
async def get_crop(
    crop_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = str(current_user.id)
    result = await db.execute(
        text(
            f"""
            SELECT {CROP_COLUMNS}
            FROM crops
            WHERE id = :id AND user_id = :user_id
            """
        ),
        {"id": crop_id, "user_id": user_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Parcela no encontrada")

    crop = _serialize_crop(dict(row))
    t_result = await db.execute(
        text(
            """
            SELECT id, crop_id, fecha, producto, materia_activa, dosis,
                   plaga_objetivo, carencia_dias, observaciones, created_at
            FROM crop_treatments
            WHERE crop_id = :crop_id
            ORDER BY fecha DESC
            """
        ),
        {"crop_id": crop_id},
    )
    treatments = []
    for r in t_result.mappings().all():
        item = dict(r)
        item["fecha"] = str(item["fecha"]) if item.get("fecha") else None
        if item.get("created_at"):
            item["created_at"] = str(item["created_at"])
        treatments.append(item)
    crop["treatments"] = treatments
    return {"status": "success", "data": crop}


@router.patch("/{crop_id}", status_code=200)
async def update_crop(
    crop_id: str,
    data: CropUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = str(current_user.id)
    raw = {k: v for k, v in data.model_dump().items() if v is not None}
    if not raw:
        raise HTTPException(status_code=400, detail="Nada que actualizar")

    # Permitir borrar polígono enviando null explícito via model — solo keys presentes
    if "poligono" in data.model_dump(exclude_unset=True):
        raw["poligono"] = data.poligono

    owned = await db.execute(
        text("SELECT id FROM crops WHERE id = :id AND user_id = :user_id"),
        {"id": crop_id, "user_id": user_id},
    )
    if not owned.first():
        raise HTTPException(status_code=404, detail="Parcela no encontrada")

    if "poligono" in raw:
        poly = normalize_polygon(raw["poligono"])
        raw["poligono"] = dumps_polygon(poly)
        if poly:
            centroid = polygon_centroid(poly)
            if centroid:
                raw.setdefault("lat", centroid[0])
                raw.setdefault("lon", centroid[1])
                # Actualizar siempre centroide al redibujar
                raw["lat"], raw["lon"] = centroid
            if "superficie_ha" not in raw:
                area = polygon_area_ha(poly)
                if area is not None:
                    raw["superficie_ha"] = area

    set_parts = []
    params: dict[str, Any] = {"id": crop_id, "user_id": user_id}
    for k, v in raw.items():
        if k == "poligono":
            set_parts.append("poligono = CAST(:poligono AS jsonb)")
        else:
            set_parts.append(f"{k} = :{k}")
        params[k] = v

    try:
        await db.execute(
            text(
                f"UPDATE crops SET {', '.join(set_parts)} "
                "WHERE id = :id AND user_id = :user_id"
            ),
            params,
        )
        await db.commit()
        return {"status": "success", "id": crop_id}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{crop_id}", status_code=200)
async def delete_crop(
    crop_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = str(current_user.id)
    try:
        result = await db.execute(
            text("DELETE FROM crops WHERE id = :id AND user_id = :user_id RETURNING id"),
            {"id": crop_id, "user_id": user_id},
        )
        if not result.first():
            raise HTTPException(status_code=404, detail="Parcela no encontrada")
        await db.commit()
        return {"status": "success", "id": crop_id}
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{crop_id}/treatments", status_code=200)
async def list_treatments(
    crop_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = str(current_user.id)
    owned = await db.execute(
        text("SELECT id FROM crops WHERE id = :id AND user_id = :user_id"),
        {"id": crop_id, "user_id": user_id},
    )
    if not owned.first():
        raise HTTPException(status_code=404, detail="Parcela no encontrada")

    result = await db.execute(
        text(
            """
            SELECT id, crop_id, fecha, producto, materia_activa, dosis,
                   plaga_objetivo, carencia_dias, observaciones, created_at
            FROM crop_treatments
            WHERE crop_id = :crop_id
            ORDER BY fecha DESC
            """
        ),
        {"crop_id": crop_id},
    )
    items = []
    for r in result.mappings().all():
        item = dict(r)
        item["fecha"] = str(item["fecha"]) if item.get("fecha") else None
        if item.get("created_at"):
            item["created_at"] = str(item["created_at"])
        items.append(item)
    return {"status": "success", "data": items}


@router.post("/{crop_id}/treatments", status_code=201)
async def create_treatment(
    crop_id: str,
    data: TreatmentCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = str(current_user.id)
    owned = await db.execute(
        text("SELECT id FROM crops WHERE id = :id AND user_id = :user_id"),
        {"id": crop_id, "user_id": user_id},
    )
    if not owned.first():
        raise HTTPException(status_code=404, detail="Parcela no encontrada")

    treatment_id = str(uuid4())
    try:
        await db.execute(
            text(
                """
                INSERT INTO crop_treatments (
                    id, crop_id, fecha, producto, materia_activa, dosis,
                    plaga_objetivo, carencia_dias, observaciones
                ) VALUES (
                    :id, :crop_id, :fecha, :producto, :materia_activa, :dosis,
                    :plaga_objetivo, :carencia_dias, :observaciones
                )
                """
            ),
            {"id": treatment_id, "crop_id": crop_id, **data.model_dump()},
        )
        await db.commit()
        return {"status": "success", "id": treatment_id}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{crop_id}/treatments/{treatment_id}", status_code=200)
async def delete_treatment(
    crop_id: str,
    treatment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = str(current_user.id)
    owned = await db.execute(
        text("SELECT id FROM crops WHERE id = :id AND user_id = :user_id"),
        {"id": crop_id, "user_id": user_id},
    )
    if not owned.first():
        raise HTTPException(status_code=404, detail="Parcela no encontrada")

    result = await db.execute(
        text(
            """
            DELETE FROM crop_treatments
            WHERE id = :id AND crop_id = :crop_id
            RETURNING id
            """
        ),
        {"id": treatment_id, "crop_id": crop_id},
    )
    if not result.first():
        raise HTTPException(status_code=404, detail="Tratamiento no encontrado")
    await db.commit()
    return {"status": "success", "id": treatment_id}
