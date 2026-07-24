import uuid
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db
from schemas.organization import OrganizationCreateRequest
from routes.auth import get_current_user
from models.user import User
from schemas.knowledge_base import KnowledgeBaseCreate
from services.knowledge_graph_service import KnowledgeGraphService
from services.rag_service import RAGService
from uuid import UUID

router = APIRouter(prefix="/organization", tags=["Organization"])

# ============================================================
# 1. Crear Organización
# ============================================================
@router.post("", status_code=201)
async def setup_organization(
    request: OrganizationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        exists = await db.scalar(
            text("SELECT id FROM organizations WHERE name = :name"),
            {"name": request.name},
        )
        if exists:
            raise HTTPException(
                status_code=400,
                detail="Ya existe una organización registrada con este nombre",
            )

        # A. Crear la Organización
        org_id = await db.scalar(
            text("""
            INSERT INTO organizations (name, description, active)
            VALUES (:name, :description, true)
            RETURNING id
            """),
            {"name": request.name, "description": request.description},
        )

        # B. Asignar el usuario creador como ORG_ADMIN global
        role_id = await db.scalar(
            text("SELECT id FROM roles WHERE name = 'ORG_ADMIN' AND organization_id IS NULL LIMIT 1")
        )
        
        if not role_id:
            raise HTTPException(status_code=500, detail="Error crítico: Rol ORG_ADMIN global no encontrado.")

        await db.execute(
            text("""
            INSERT INTO organization_members (organization_id, user_id, role_id, active)
            VALUES (:org_id, :user_id, :role_id, true)
            """),
            {"org_id": org_id, "user_id": current_user.id, "role_id": role_id}
        )

        # C. Crear Tenant
        tenant_id = await db.scalar(
            text("""
            INSERT INTO tenants (organization_id, name, description, active)
            VALUES (:org_id, 'Tenant Predeterminado', 'Instancia por defecto de la organización', true)
            RETURNING id
            """),
            {"org_id": org_id},
        )

        # D. Crear Knowledge Base Base (Aislamiento por colecciones de ChromaDB)
        chroma_collection_name = f"col_{str(tenant_id).replace('-', '')}"
        kb_id = await db.scalar(
            text("""
            INSERT INTO knowledge_bases (tenant_id, name, description, chroma_collection, created_by)
            VALUES (:tenant_id, 'Base de Conocimiento General',
                    'Repositorio predeterminado para el procesamiento de documentos RAG.',
                    :chroma, :user_id)
            RETURNING id
            """),
            {"tenant_id": tenant_id, "chroma": chroma_collection_name, "user_id": current_user.id},
        )

        await db.commit()

        return {
            "status": "success",
            "message": "Estructura multi-tenant y Base de Conocimiento inicializadas correctamente.",
            "organization_id": str(org_id),
            "tenant_id": str(tenant_id),
            "default_knowledge_base_id": str(kb_id),
        }

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al inicializar la infraestructura: {e}")

# ============================================================
# 2. Listar Organizaciones del Usuario Autenticado
# ============================================================
@router.get("", status_code=200)
async def list_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Nombre de tu organización global comunitaria
    GLOBAL_ORG_NAME = "AgroTech"

    result = await db.execute(
        text("""
            SELECT 
                o.id, 
                o.name, 
                o.description, 
                CASE WHEN o.active THEN 'ACTIVE' ELSE 'INACTIVE' END as status,
                CASE WHEN o.name = :global_name THEN true ELSE false END as is_global
            FROM organizations o
            -- Hacemos un LEFT JOIN filtrando por el usuario actual
            LEFT JOIN organization_members om 
                ON o.id = om.organization_id AND om.user_id = :user_id
            -- Traemos la organización si el usuario es miembro, o si es la global
            WHERE (om.user_id IS NOT NULL OR o.name = :global_name)
              AND o.active = true
            -- Ordenamos para que la global salga primero, y luego alfabéticamente
            ORDER BY is_global DESC, o.name
        """),
        {
            "user_id": current_user.id, 
            "global_name": GLOBAL_ORG_NAME
        }
    )
    return result.mappings().all()

# ============================================================
# 3. Obtener Detalles de una Organización
# ============================================================
@router.get("/{organization_id}")
async def get_organization(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    organization = (
        await db.execute(
            text("""
                SELECT
                    o.id, o.name, o.description, o.active
                FROM organizations o
                JOIN organization_members om ON o.id = om.organization_id
                WHERE o.id = :id AND om.user_id = :user_id
            """),
            {"id": organization_id, "user_id": current_user.id},
        )
    ).mappings().first()

    if not organization:
        raise HTTPException(status_code=404, detail="Organización no encontrada o acceso denegado")

    return organization

# ============================================================
# 4. Desactivar Organización
# ============================================================
@router.patch("/{organization_id}/deactivate")
async def deactivate_organization(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Idealmente, aquí deberías verificar que el user tenga el rol 'ORG_ADMIN'
    await db.execute(
        text("""
            UPDATE organizations
            SET active=false
            WHERE id=:id AND EXISTS (
                SELECT 1 FROM organization_members WHERE organization_id = :id AND user_id = :user_id
            )
        """),
        {"id": organization_id, "user_id": current_user.id},
    )
    await db.commit()
    return {"status": "deactivated"}

# ============================================================
# 5. Activar Organización
# ============================================================
@router.patch("/{organization_id}/activate")
async def activate_organization(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        text("""
            UPDATE organizations
            SET active=true
            WHERE id=:id AND EXISTS (
                SELECT 1 FROM organization_members WHERE organization_id = :id AND user_id = :user_id
            )
        """),
        {"id": organization_id, "user_id": current_user.id},
    )
    await db.commit()
    return {"status": "activated"}

# ============================================================
# 6. Eliminar Organización
# ============================================================
@router.delete("/{organization_id}")
async def delete_organization(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        text("""
            DELETE FROM organizations
            WHERE id=:id AND EXISTS (
                SELECT 1 FROM organization_members WHERE organization_id = :id AND user_id = :user_id
            )
        """),
        {"id": organization_id, "user_id": current_user.id},
    )
    await db.commit()
    return {"status":"deleted"}

# ============================================================
# 7. Obtener Miembros de una Organización
# ============================================================
@router.get("/{organization_id}/members")
async def get_members(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verificamos seguridad para que no saquen datos sin pertenecer
    check = await db.scalar(
        text("SELECT 1 FROM organization_members WHERE organization_id = :org_id AND user_id = :user_id"),
        {"org_id": organization_id, "user_id": current_user.id}
    )
    if not check:
        raise HTTPException(status_code=403, detail="No perteneces a esta organización")

    members = (
        await db.execute(
            text("""
                SELECT
                    u.id, u.name, u.email, r.name AS role
                FROM organization_members om
                JOIN users u ON u.id = om.user_id
                LEFT JOIN roles r ON r.id = om.role_id
                WHERE om.organization_id = :id
                ORDER BY u.name
            """),
            {"id": organization_id},
        )
    ).mappings().all()

    return members

# ============================================================
# 8. Obtener Departamentos de la Organización
# ============================================================
@router.get("/{organization_id}/departments", status_code=200)
async def get_departments(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Aislamiento de lectura
    check = await db.scalar(
        text("SELECT 1 FROM organization_members WHERE organization_id = :org_id AND user_id = :user_id"),
        {"org_id": organization_id, "user_id": current_user.id}
    )
    if not check:
        raise HTTPException(status_code=403, detail="No perteneces a esta organización")

    result = await db.execute(
        text("""
            SELECT id, name, description 
            FROM departments 
            WHERE organization_id = :org_id 
            ORDER BY name
        """),
        {"org_id": organization_id},
    )
    return result.mappings().all()

# ============================================================
# 9. Knowledge Map (Grafo RAG)
# ============================================================
@router.get("/{organization_id}/knowledge-map")
async def graph(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    organization = await db.execute(
        text("""
            SELECT o.id, o.name, o.description
            FROM organizations o
            JOIN organization_members om ON o.id = om.organization_id
            WHERE o.id = :id AND o.active = true AND om.user_id = :user_id
        """),
        {"id": organization_id, "user_id": current_user.id}
    )
    organization = organization.mappings().first()

    if not organization:
        raise HTTPException(status_code=404, detail="Organización no encontrada o acceso denegado")

    tenant = await db.execute(
        text("""
            SELECT id FROM tenants
            WHERE organization_id = :org_id AND active = true
            LIMIT 1
        """),
        {"org_id": organization_id}
    )
    tenant_id = tenant.scalar()

    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    rag = RAGService()
    graph_service = KnowledgeGraphService(rag.collection)
    graph_data = await graph_service.build_graph()

    return {
        "organization": {
            "id": str(organization["id"]),
            "name": organization["name"],
            "description": organization["description"],
        },
        "statistics": {
            "nodes": len(graph_data["nodes"]),
            "edges": len(graph_data["edges"]),
            "documents": len([n for n in graph_data["nodes"] if n["type"] == "document"]),
            "chunks": len([n for n in graph_data["nodes"] if n["type"] == "chunk"])
        },
        "graph": graph_data
    }