from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.security import user_is_admin
from models.user import User
from identity.http import get_current_user
from services.database import get_db
from opendata import service as opendata_service

router = APIRouter(prefix="/opendata", tags=["OpenData"])


async def require_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not await user_is_admin(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden importar datos abiertos.",
        )
    return current_user


@router.post("/import")
async def import_opendata(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        return await opendata_service.import_opendata_directory(db)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Error importando opendata: {exc}"
        ) from exc


@router.get("/sat")
async def get_sat(
    municipio: Optional[str] = Query(None),
    situacion: Optional[str] = Query(None),
    cnae_contains: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = await opendata_service.list_sat_societies(
        db,
        municipio=municipio,
        situacion=situacion,
        cnae_contains=cnae_contains,
        limit=limit,
    )
    return {"status": "success", "count": len(rows), "data": rows}


@router.get("/istac/series")
async def get_istac_series(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = await opendata_service.list_istac_series(db)
    return {"status": "success", "count": len(rows), "data": rows}


@router.get("/istac/series/{series_id}/observations")
async def get_istac_observations(
    series_id: str,
    limit: int = Query(200, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = await opendata_service.list_istac_observations(
        db, series_id, limit=limit
    )
    return {
        "status": "success",
        "series_id": series_id,
        "count": len(rows),
        "data": rows,
    }
