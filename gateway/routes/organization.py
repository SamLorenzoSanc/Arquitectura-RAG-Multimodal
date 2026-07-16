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

        org_id = await db.scalar(
            text("""
            INSERT INTO organizations (name, description, active)
            VALUES (:name, :description, true)
            RETURNING id
            """),
            {"name": request.name, "description": request.description},
        )

        tenant_id = await db.scalar(
            text("""
            INSERT INTO tenants (organization_id, name, description, active)
            VALUES (:org_id, 'Tenant Predeterminado', 'Instancia por defecto de la organización', true)
            RETURNING id
            """),
            {"org_id": org_id},
        )

        await db.execute(
            text("""
            INSERT INTO roles (organization_id, name, description)
            VALUES (:org_id, 'user', 'Rol básico predeterminado para miembros')
            """),
            {"org_id": org_id},
        )

        chroma_collection_name = f"default_collection_{str(tenant_id)[:8]}"
        kb_id = await db.scalar(
            text("""
            INSERT INTO knowledge_bases (tenant_id, name, description, chroma_collection, created_by)
            VALUES (:tenant_id, 'Base de Conocimiento General',
                    'Repositorio predeterminado para el procesamiento de documentos RAG.',
                    :chroma, NULL)
            RETURNING id
            """),
            {"tenant_id": tenant_id, "chroma": chroma_collection_name},
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
                    id,
                    name,
                    description,
                    active
                FROM organizations
                WHERE id=:id
            """),
            {"id": organization_id},
        )
    ).mappings().first()

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organización no encontrada",
        )

    return organization

@router.patch("/{organization_id}/deactivate")
async def deactivate_organization(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        text("""
            UPDATE organizations
            SET active=false
            WHERE id=:id
        """),
        {"id": organization_id},
    )

    await db.commit()

    return {"status": "deactivated"}

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
            WHERE id=:id
        """),
        {"id": organization_id},
    )

    await db.commit()

    return {"status": "activated"}

@router.delete("/{organization_id}")
async def delete_organization(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        text("""
            DELETE FROM organizations
            WHERE id=:id
        """),
        {"id": organization_id},
    )

    await db.commit()

    return {"status":"deleted"}

@router.get("/{organization_id}/members")
async def get_members(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    members = (
        await db.execute(
            text("""
                SELECT
                    u.id,
                    u.name,
                    u.email,
                    r.name AS role
                FROM organization_members om
                JOIN users u
                    ON u.id = om.user_id
                LEFT JOIN roles r
                    ON r.id = om.role_id
                WHERE om.organization_id=:id
                ORDER BY u.name
            """),
            {"id": organization_id},
        )
    ).mappings().all()

    return members
@router.get("", status_code=200)
async def list_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("""
            SELECT id, name, description, 
                   CASE WHEN active THEN 'ACTIVE' ELSE 'INACTIVE' END as status 
            FROM organizations 
            ORDER BY name
        """)
    )
    return result.mappings().all()


@router.get("/{organization_id}/departments", status_code=200)
async def get_departments(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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

@router.get("/{organization_id}/knowledge-map")
async def graph(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    organization = await db.execute(
        text("""
            SELECT
                id,
                name,
                description
            FROM organizations
            WHERE id = :id
              AND active = true
        """),
        {
            "id": organization_id
        }
    )

    organization = organization.mappings().first()

    if not organization:

        raise HTTPException(
            status_code=404,
            detail="Organización no encontrada"
        )

    tenant = await db.execute(
        text("""
            SELECT
                id
            FROM tenants
            WHERE organization_id = :org_id
              AND active = true
            LIMIT 1
        """),
        {
            "org_id": organization_id
        }
    )

    tenant = tenant.scalar()

    if not tenant:

        raise HTTPException(
            status_code=404,
            detail="Tenant no encontrado"
        )

    rag = RAGService(
    )

    graph_service = KnowledgeGraphService(
        rag.collection
    )


    graph = await graph_service.build_graph()


    return {
        "organization": {
            "id":
                str(organization["id"]),
            "name":
                organization["name"],
            "description":
                organization["description"],
        },


        "statistics": {
            "nodes":
                len(graph["nodes"]),
            "edges":
                len(graph["edges"]),
            "documents":
                len(
                    [
                        n for n in graph["nodes"]
                        if n["type"] == "document"
                    ]
                ),
            "chunks":
                len(
                    [
                        n for n in graph["nodes"]
                        if n["type"] == "chunk"
                    ]
                )
        },
        "graph": graph

    }