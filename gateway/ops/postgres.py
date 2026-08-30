from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class OpsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ping(self) -> bool:
        try:
            await self.db.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def counts(self) -> dict:
        users = await self.db.scalar(text("SELECT COUNT(*) FROM users"))
        documents = await self.db.scalar(text("SELECT COUNT(*) FROM documents"))
        conversations = await self.db.scalar(text("SELECT COUNT(*) FROM conversations"))
        messages = await self.db.scalar(text("SELECT COUNT(*) FROM messages"))
        jobs = (
            await self.db.execute(
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
            "users": users,
            "documents": documents,
            "conversations": conversations,
            "messages": messages,
            "jobs": dict(jobs) if jobs else {},
        }
