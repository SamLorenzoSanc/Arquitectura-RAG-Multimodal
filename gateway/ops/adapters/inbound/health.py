import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ops.adapters.outbound.postgres import OpsRepository
from services.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health():
    return {"gateway": "running"}


@router.get("/ready")
async def readiness(response: Response, db: AsyncSession = Depends(get_db)):
    db_ok = await OpsRepository(db).ping()
    if not db_ok:
        logger.error("Readiness check: database unreachable")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "gateway": "running",
        "database": "ok" if db_ok else "unreachable",
    }
