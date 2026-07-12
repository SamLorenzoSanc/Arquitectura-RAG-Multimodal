from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import uuid4
from services.database import get_db
from .auth import get_current_user
from schemas.knowledge_base import KnowledgeBaseCreate


router = APIRouter(prefix="/knowledge", tags=["knowledge"])

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    kb: KnowledgeBaseCreate, 
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    kb_id = str(uuid4())
    tenant_id = current_user.get("tenant_id")

    if not tenant_id:
        raise HTTPException(
            status_code=403, 
            detail="El usuario no tiene un Tenant activo asignado para crear una Base de Conocimiento."
        )

    try:
        db.execute(
            text("""
            INSERT INTO knowledge_bases (id, tenant_id, name, description, created_at)
            VALUES (:id, :tenant_id, :name, :description, NOW())
            """),
            {
                "id": kb_id,
                "tenant_id": tenant_id,
                "name": kb.name,
                "description": kb.description
            }
        )
        db.commit()
        
        return {
            "knowledge_base_id": kb_id,
            "name": kb.name,
            "tenant_id": tenant_id,
            "status": "created"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear la Base de Conocimiento: {str(e)}")


@router.get("/{knowledge_base_id}")
async def get_knowledge_base(
    knowledge_base_id: str, 
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    tenant_id = current_user.get("tenant_id")

    kb = db.execute(
        text("""
        SELECT id, tenant_id, name, description, created_at 
        FROM knowledge_bases 
        WHERE id = :kb_id AND tenant_id = :tenant_id
        """),
        {"kb_id": knowledge_base_id, "tenant_id": tenant_id}
    ).mappings().first()

    if not kb:
        raise HTTPException(
            status_code=404, 
            detail="Base de Conocimiento no encontrada o no tienes permisos para verla."
        )

    return kb