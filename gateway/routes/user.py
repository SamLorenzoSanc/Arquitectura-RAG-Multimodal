from fastapi import APIRouter
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from services.database import SessionLocal

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.get("/")
async def list_users():

    db = SessionLocal()

    users = db.execute(
        text("""
        SELECT
            id,
            name,
            email,
            active,
            created_at
        FROM users
        """)
    ).mappings().all()

    db.close()

    return users

@router.get("/roles")
async def list_roles():
    db = SessionLocal()
    roles = db.execute(
        text("SELECT id, name, description, organization_id FROM roles")
    ).mappings().all()
    db.close()
    return roles