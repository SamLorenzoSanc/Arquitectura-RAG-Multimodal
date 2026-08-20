from datetime import datetime, timezone
import time
import psutil

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ops.adapters.outbound.postgres import OpsRepository
from services.database import get_db

router = APIRouter(prefix="/metrics", tags=["Metrics"])

START_TIME = time.time()


@router.get("/")
async def metrics(db: AsyncSession = Depends(get_db)):
    counts = await OpsRepository(db).counts()
    jobs = counts["jobs"]
    return {
        "server": {
            "uptime_seconds": round(time.time() - START_TIME),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
        },
        "database": {
            "users": counts["users"],
            "documents": counts["documents"],
            "conversations": counts["conversations"],
            "messages": counts["messages"],
        },
        "processing": {
            "pending": jobs.get("pending"),
            "processing": jobs.get("processing"),
            "completed": jobs.get("completed"),
            "failed": jobs.get("failed"),
        },
    }
