from typing import List, Union
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from services.database import get_db
from .auth import get_current_user

router = APIRouter(prefix="/crops", tags=["Crops"])


class CropCreateSchema(BaseModel):
    nombre: str
    cultivo: str
    isla: str
    lat: float
    lon: float
    temperatura: float
    humedad: float
    lluvia: float
    viento: float
    ndvi: float
    sentinel_tile: Optional[str] = None


@router.post("/", status_code=201)
async def create_crop(
    data: Union[CropCreateSchema, List[CropCreateSchema]],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),  # Inyecta el objeto usuario completo
):
    # Extraemos el ID del usuario en formato string (ajusta .id según el atributo de tu modelo User)
    user_id = str(current_user.id)

    # Normalizamos para procesar siempre como lista
    items = data if isinstance(data, list) else [data]
    created_ids = []

    query = text("""
        INSERT INTO crops (
            id, user_id, nombre, cultivo, isla, lat, lon,
            temperatura, humedad, lluvia, viento, ndvi, sentinel_tile
        ) VALUES (
            :id, :user_id, :nombre, :cultivo, :isla, :lat, :lon,
            :temperatura, :humedad, :lluvia, :viento, :ndvi, :sentinel_tile
        )
    """)

    try:
        for crop in items:
            crop_id = str(uuid4())
            await db.execute(
                query, {"id": crop_id, "user_id": user_id, **crop.model_dump()}
            )
            created_ids.append(crop_id)

        await db.commit()
        return {
            "ids": created_ids,
            "status": "success",
            "message": f"Se ha(n) creado {len(created_ids)} cultivo(s) correctamente",
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al guardar el cultivo: {str(e)}"
        )


@router.get("/", status_code=200)
async def get_user_crops(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),  # Inyecta el objeto usuario
):
    user_id = str(current_user.id)  # Extrae el ID en string
    try:
        query = text("""
            SELECT id, user_id, nombre, cultivo, isla, lat, lon,
                   temperatura, humedad, lluvia, viento, ndvi, sentinel_tile
            FROM crops
            WHERE user_id = :user_id
        """)
        result = await db.execute(query, {"user_id": user_id})
        crops = result.mappings().all()

        return {"status": "success", "data": [dict(crop) for crop in crops]}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener los cultivos: {str(e)}"
        )
