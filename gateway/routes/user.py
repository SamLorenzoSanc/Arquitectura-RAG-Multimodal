from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/")
async def list_users(db: AsyncSession = Depends(get_db)):
    users = (
        await db.execute(
            text("""
            SELECT id, name, email, active, created_at
            FROM users
            """)
        )
    ).mappings().all()
    return users


@router.get("/roles")
async def list_roles(db: AsyncSession = Depends(get_db)):
    roles = (
        await db.execute(
            text("SELECT id, name, description, organization_id FROM roles")
        )
    ).mappings().all()
    return roles