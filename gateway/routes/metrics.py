from datetime import datetime, timezone
import time
import psutil

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from services.database import get_db

router = APIRouter(prefix="/metrics", tags=["Metrics"])

START_TIME = time.time()


@router.get("/")
async def metrics(db: AsyncSession = Depends(get_db)):
    # Conteos base (una query por tabla)
    users = await db.scalar(text("SELECT COUNT(*) FROM users"))
    documents = await db.scalar(text("SELECT COUNT(*) FROM documents"))
    conversations = await db.scalar(text("SELECT COUNT(*) FROM conversations"))
    messages = await db.scalar(text("SELECT COUNT(*) FROM messages"))

    # Los 4 estados de jobs en UNA sola query con FILTER
    jobs = (
        await db.execute(
            text("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'PENDING')    AS pending,
                COUNT(*) FILTER (WHERE status = 'PROCESSING') AS processing,
                COUNT(*) FILTER (WHERE status = 'COMPLETED')  AS completed,
                COUNT(*) FILTER (WHERE status = 'FAILED')     AS failed
            FROM processing_jobs
            """)
        )
    ).mappings().first()

    return {
        "server": {
            "uptime_seconds": round(time.time() - START_TIME),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
        },
        "database": {
            "users": users,
            "documents": documents,
            "conversations": conversations,
            "messages": messages,
        },
        "processing": {
            "pending": jobs["pending"],
            "processing": jobs["processing"],
            "completed": jobs["completed"],
            "failed": jobs["failed"],
        },
    }