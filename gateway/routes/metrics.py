from datetime import datetime
import time
import psutil

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from services.database import get_db

router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"]
)

START_TIME = time.time()

@router.get("/")
async def metrics(db: Session = Depends(get_db)):

    users = db.execute(
        text("SELECT COUNT(*) FROM users")
    ).scalar()

    documents = db.execute(
        text("SELECT COUNT(*) FROM documents")
    ).scalar()

    conversations = db.execute(
        text("SELECT COUNT(*) FROM conversations")
    ).scalar()

    messages = db.execute(
        text("SELECT COUNT(*) FROM messages")
    ).scalar()

    pending_jobs = db.execute(
        text("""
            SELECT COUNT(*)
            FROM processing_jobs
            WHERE status='PENDING'
        """)
    ).scalar()

    processing_jobs = db.execute(
        text("""
            SELECT COUNT(*)
            FROM processing_jobs
            WHERE status='PROCESSING'
        """)
    ).scalar()

    completed_jobs = db.execute(
        text("""
            SELECT COUNT(*)
            FROM processing_jobs
            WHERE status='COMPLETED'
        """)
    ).scalar()

    failed_jobs = db.execute(
        text("""
            SELECT COUNT(*)
            FROM processing_jobs
            WHERE status='FAILED'
        """)
    ).scalar()

    return {

        "server": {
            "uptime_seconds": round(time.time() - START_TIME),
            "timestamp": datetime.now(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent
        },

        "database": {
            "users": users,
            "documents": documents,
            "conversations": conversations,
            "messages": messages
        },

        "processing": {
            "pending": pending_jobs,
            "processing": processing_jobs,
            "completed": completed_jobs,
            "failed": failed_jobs
        }

    }