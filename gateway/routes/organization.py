from uuid import uuid4
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from services.database import SessionLocal
from schemas.organization import OrganizationCreateRequest 

router = APIRouter(prefix="/organization", tags=["Organization"])

@router.post("/", status_code=201)
async def setup_organization(request: OrganizationCreateRequest):
    db = SessionLocal()
    try:
        # 1. Validar si ya existe la organización
        exists = db.execute(
            text("SELECT id FROM organizations WHERE name = :name"),
            {"name": request.name}
        ).first()

        if exists:
            raise HTTPException(
                status_code=400, 
                detail="Ya existe una organización registrada con este nombre"
            )

        # 2. Insertar la nueva organización
        org_result = db.execute(
            text("""
            INSERT INTO organizations (name, description, active)
            VALUES (:name, :description, true)
            RETURNING id
            """),
            {"name": request.name, "description": request.description}
        ).first()
        org_id = org_result[0]

        # 3. Crear automáticamente el Tenant por defecto de esta organización
        tenant_result = db.execute(
            text("""
            INSERT INTO tenants (organization_id, name, description, active)
            VALUES (:org_id, 'Tenant Predeterminado', 'Instancia por defecto de la organización', true)
            RETURNING id
            """),
            {"org_id": org_id}
        ).first()
        tenant_id = tenant_result[0]

        # 4. Crear el rol básico 'user'
        db.execute(
            text("""
            INSERT INTO roles (organization_id, name, description)
            VALUES (:org_id, 'user', 'Rol básico predeterminado para miembros')
            """),
            {"org_id": org_id}
        )


        chroma_collection_name = f"default_collection_{str(tenant_id)[:8]}"
        
        kb_result = db.execute(
            text("""
            INSERT INTO knowledge_bases (tenant_id, name, description, chroma_collection, created_by)
            VALUES (:tenant_id, 'Base de Conocimiento General', 'Repositorio predeterminado para el procesamiento de documentos RAG.', :chroma, NULL)
            RETURNING id
            """),
            {
                "tenant_id": tenant_id,
                "chroma": chroma_collection_name
            }
        ).first()
        kb_id = kb_result[0]

        db.commit()
        
        return {
            "status": "success",
            "message": "Estructura multi-tenant y Base de Conocimiento inicializadas correctamente.",
            "organization_id": str(org_id),
            "tenant_id": str(tenant_id),
            "default_knowledge_base_id": str(kb_id)
        }

    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error al inicializar la infraestructura: {str(e)}")
    finally:
        db.close()