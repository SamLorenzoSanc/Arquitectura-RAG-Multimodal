from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.user import User
from services.database import get_db
from routes.auth import get_current_user

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

@router.get("/me/roles")
async def get_my_roles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    roles = await db.execute(
        text("""
            SELECT 
                o.id AS organization_id,
                o.name AS organization_name,
                r.name AS role_name,
                r.description AS role_description
            FROM organization_members om
            JOIN organizations o ON o.id = om.organization_id
            LEFT JOIN roles r ON r.id = om.role_id
            WHERE om.user_id = :user_id AND om.active = true
        """),
        {"user_id": current_user.id}
    )
    
    return roles.mappings().all()