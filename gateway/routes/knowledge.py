from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import uuid4

from services.database import get_db

from .auth import get_current_user
from models.user import User
from schemas.knowledge_base import KnowledgeBaseCreate

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


async def _resolve_tenant_id(db: AsyncSession, user_id) -> str | None:
    """Tenant activo del usuario vía su organización. None si no tiene."""
    return await db.scalar(
        text("""
        SELECT t.id
        FROM organization_members om
        JOIN tenants t ON t.organization_id = om.organization_id
        WHERE om.user_id = :user_id AND om.active = true AND t.active = true
        LIMIT 1
        """),
        {"user_id": user_id},
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    kb: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await _resolve_tenant_id(db, current_user.id)
    if not tenant_id:
        raise HTTPException(
            status_code=403,
            detail="El usuario no tiene un Tenant activo asignado para crear una Base de Conocimiento.",
        )

    kb_id = str(uuid4())
    try:
        await db.execute(
            text("""
            INSERT INTO knowledge_bases (id, tenant_id, name, description, chroma_collection, created_by, created_at)
            VALUES (:id, :tenant_id, :name, :description, :chroma_collection, :created_by, NOW())
            """),
            {
                "id": kb_id,
                "tenant_id": tenant_id,
                "name": kb.name,
                "description": kb.description,
                "chroma_collection": f"kb_{kb_id.replace('-', '')}",
                "created_by": current_user.id,
            },
        )
        await db.commit()

        return {
            "knowledge_base_id": kb_id,
            "name": kb.name,
            "tenant_id": str(tenant_id),
            "status": "created",
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear la Base de Conocimiento: {e}")

@router.get("/current")
async def get_current_knowledge_base(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await _resolve_tenant_id(db, current_user.id)

    if not tenant_id:
        raise HTTPException(
            status_code=403,
            detail="El usuario no tiene un Tenant activo asignado.",
        )

    kb = (
        await db.execute(
            text("""
            SELECT
                id,
                tenant_id,
                name,
                description,
                chroma_collection,
                created_by,
                created_at
            FROM knowledge_bases
            WHERE tenant_id = :tenant_id
            ORDER BY created_at ASC
            LIMIT 1
            """),
            {"tenant_id": tenant_id},
        )
    ).mappings().first()

    if not kb:
        raise HTTPException(
            status_code=404,
            detail="No existe ninguna Base de Conocimiento para este tenant.",
        )

    return {
        "id": str(kb["id"]),
        "tenant_id": str(kb["tenant_id"]),
        "name": kb["name"],
        "description": kb["description"],
        "chroma_collection": kb["chroma_collection"],
        "created_by": str(kb["created_by"]),
        "created_at": kb["created_at"],
    }

@router.get("/{knowledge_base_id}")
async def get_knowledge_base(
    knowledge_base_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await _resolve_tenant_id(db, current_user.id)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Base de Conocimiento no encontrada o no tienes permisos para verla.")

    kb = (
        await db.execute(
            text("""
            SELECT id, tenant_id, name, description, created_at
            FROM knowledge_bases
            WHERE id = :kb_id AND tenant_id = :tenant_id
            """),
            {"kb_id": knowledge_base_id, "tenant_id": tenant_id},
        )
    ).mappings().first()

    if not kb:
        raise HTTPException(status_code=404, detail="Base de Conocimiento no encontrada o no tienes permisos para verla.")

    return kb