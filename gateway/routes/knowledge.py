from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import uuid4, UUID

from services.database import get_db

from .auth import get_current_user
from models.user import User
from schemas.knowledge_base import KnowledgeBaseCreate
from utils.tenant import get_user_tenant_id

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    kb: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    organization_id: UUID | None = Query(None),
):
    tenant_id = await get_user_tenant_id(
        current_user.id, db, organization_id=organization_id
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
        raise HTTPException(
            status_code=500, detail=f"Error al crear la Base de Conocimiento: {e}"
        )


@router.get("/")
async def list_knowledge_bases(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    organization_id: UUID | None = Query(None),
):
    """Lista KBs del tenant. Preferir organization_id para aislamiento multitenant."""
    tenant_id = await get_user_tenant_id(
        current_user.id, db, organization_id=organization_id
    )

    result = await db.execute(
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
        """),
        {"tenant_id": tenant_id},
    )
    rows = result.mappings().all()
    return [
        {
            "id": str(row["id"]),
            "tenant_id": str(row["tenant_id"]),
            "name": row["name"],
            "description": row["description"],
            "chroma_collection": row["chroma_collection"],
            "created_by": str(row["created_by"]) if row["created_by"] else None,
            "created_at": row["created_at"],
        }
        for row in rows
    ]


@router.get("/current")
async def get_current_knowledge_base(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    organization_id: UUID | None = Query(None),
):
    tenant_id = await get_user_tenant_id(
        current_user.id, db, organization_id=organization_id
    )

    kb = (
        (
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
        )
        .mappings()
        .first()
    )

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
    organization_id: UUID | None = Query(None),
):
    tenant_id = await get_user_tenant_id(
        current_user.id, db, organization_id=organization_id
    )

    kb = (
        (
            await db.execute(
                text("""
            SELECT id, tenant_id, name, description, created_at
            FROM knowledge_bases
            WHERE id = :kb_id AND tenant_id = :tenant_id
            """),
                {"kb_id": knowledge_base_id, "tenant_id": tenant_id},
            )
        )
        .mappings()
        .first()
    )

    if not kb:
        raise HTTPException(
            status_code=404,
            detail="Base de Conocimiento no encontrada o no tienes permisos para verla.",
        )

    return kb
