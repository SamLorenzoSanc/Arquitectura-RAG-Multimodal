import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health():
    """Liveness: el proceso responde. No toca dependencias."""
    return {"gateway": "running"}


@router.get("/ready")
async def readiness(response: Response, db: AsyncSession = Depends(get_db)):
    """Readiness: comprueba que el gateway llega a Postgres."""
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        logger.exception("Readiness check: database unreachable")
        db_ok = False

    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "gateway": "running",
        "database": "ok" if db_ok else "unreachable",
    }