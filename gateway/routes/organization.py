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
from utils.global_org import GLOBAL_ORG_NAME, ensure_agrotech_membership
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
            text(
                "SELECT id FROM roles WHERE name = 'ORG_ADMIN' AND organization_id IS NULL LIMIT 1"
            )
        )

        if not role_id:
            raise HTTPException(
                status_code=500,
                detail="Error crítico: Rol ORG_ADMIN global no encontrado.",
            )

        await db.execute(
            text("""
            INSERT INTO organization_members (organization_id, user_id, role_id, active)
            VALUES (:org_id, :user_id, :role_id, true)
            """),
            {"org_id": org_id, "user_id": current_user.id, "role_id": role_id},
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
            {
                "tenant_id": tenant_id,
                "chroma": chroma_collection_name,
                "user_id": current_user.id,
            },
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
        raise HTTPException(
            status_code=500, detail=f"Error al inicializar la infraestructura: {e}"
        )


# ============================================================
# 2. Listar Organizaciones del Usuario Autenticado
# ============================================================
async def _ensure_global_org_membership(db: AsyncSession, user_id) -> None:
    """Garantiza que el usuario sea miembro de AgroTech (org global por defecto)."""
    await ensure_agrotech_membership(db, user_id)
    await db.commit()


@router.get("", status_code=200)
async def list_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Auto-inscripción en AgroTech para que todos la vean y puedan usarla.
    await _ensure_global_org_membership(db, current_user.id)

    result = await db.execute(
        text("""
            SELECT
                o.id,
                o.name,
                o.description,
                CASE WHEN o.active THEN 'ACTIVE' ELSE 'INACTIVE' END as status,
                CASE WHEN lower(o.name) = lower(:global_name) THEN true ELSE false END as is_global
            FROM organizations o
            INNER JOIN organization_members om
                ON o.id = om.organization_id
               AND om.user_id = :user_id
               AND om.active = true
            WHERE o.active = true
            ORDER BY is_global DESC, o.name
        """),
        {"user_id": current_user.id, "global_name": GLOBAL_ORG_NAME},
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
    await _ensure_global_org_membership(db, current_user.id)

    organization = (
        (
            await db.execute(
                text("""
                SELECT
                    o.id, o.name, o.description, o.active
                FROM organizations o
                LEFT JOIN organization_members om
                    ON o.id = om.organization_id
                   AND om.user_id = :user_id
                   AND om.active = true
                WHERE o.id = :id
                  AND o.active = true
                  AND (
                    om.user_id IS NOT NULL
                    OR lower(o.name) = lower(:global_name)
                  )
            """),
                {
                    "id": organization_id,
                    "user_id": current_user.id,
                    "global_name": GLOBAL_ORG_NAME,
                },
            )
        )
        .mappings()
        .first()
    )

    if not organization:
        raise HTTPException(
            status_code=404, detail="Organización no encontrada o acceso denegado"
        )

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
    return {"status": "deleted"}


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
        text(
            "SELECT 1 FROM organization_members WHERE organization_id = :org_id AND user_id = :user_id"
        ),
        {"org_id": organization_id, "user_id": current_user.id},
    )
    if not check:
        raise HTTPException(status_code=403, detail="No perteneces a esta organización")

    members = (
        (
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
        )
        .mappings()
        .all()
    )

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
        text(
            "SELECT 1 FROM organization_members WHERE organization_id = :org_id AND user_id = :user_id"
        ),
        {"org_id": organization_id, "user_id": current_user.id},
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
# 8b. Knowledge Bases de la Organización
# ============================================================
@router.get("/{organization_id}/knowledge-bases", status_code=200)
async def list_organization_knowledge_bases(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    check = await db.scalar(
        text(
            """
            SELECT 1 FROM organization_members
            WHERE organization_id = :org_id AND user_id = :user_id AND active = true
            """
        ),
        {"org_id": organization_id, "user_id": current_user.id},
    )
    if not check:
        raise HTTPException(status_code=403, detail="No perteneces a esta organización")

    tenant_id = await db.scalar(
        text(
            """
            SELECT id FROM tenants
            WHERE organization_id = :org_id AND active = true
            LIMIT 1
            """
        ),
        {"org_id": organization_id},
    )
    if not tenant_id:
        return []

    result = await db.execute(
        text(
            """
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
            """
        ),
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
            "organization_id": str(organization_id),
        }
        for row in rows
    ]


# ============================================================
# 9. Knowledge Map (Grafo RAG)
# ============================================================
@router.get("/{organization_id}/knowledge-map")
async def graph(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    preview: bool = False,
    knowledge_base_id: UUID | None = None,
    similarity_threshold: float = 0.45,
    max_neighbors: int = 8,
):
    organization = await db.execute(
        text("""
            SELECT o.id, o.name, o.description
            FROM organizations o
            JOIN organization_members om ON o.id = om.organization_id
            WHERE o.id = :id AND o.active = true AND om.user_id = :user_id
        """),
        {"id": organization_id, "user_id": current_user.id},
    )
    organization = organization.mappings().first()

    if not organization:
        raise HTTPException(
            status_code=404, detail="Organización no encontrada o acceso denegado"
        )

    tenant = await db.execute(
        text("""
            SELECT id FROM tenants
            WHERE organization_id = :org_id AND active = true
            LIMIT 1
        """),
        {"org_id": organization_id},
    )
    tenant_id = tenant.scalar()

    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    kb_id = str(knowledge_base_id) if knowledge_base_id else None
    if kb_id:
        kb_ok = await db.scalar(
            text(
                """
                SELECT 1 FROM knowledge_bases
                WHERE id = :kb_id AND tenant_id = :tenant_id
                """
            ),
            {"kb_id": kb_id, "tenant_id": tenant_id},
        )
        if not kb_ok:
            raise HTTPException(
                status_code=404,
                detail="Knowledge base no encontrada en esta organización",
            )

    # No pasar collection Chroma: forzar lectura pgvector filtrada por tenant/KB
    graph_service = KnowledgeGraphService(collection=None)
    graph_data = await graph_service.build_graph(
        tenant_id=str(tenant_id),
        preview=preview,
        knowledge_base_id=kb_id,
        similarity_threshold=similarity_threshold,
        max_neighbors=max_neighbors,
    )

    stats = graph_data.get("stats") or {}
    chunk_nodes = [n for n in graph_data["nodes"] if n.get("type") == "chunk"]
    doc_nodes = [n for n in graph_data["nodes"] if n.get("type") == "document"]
    documents_count = stats.get("documents") or (
        len(doc_nodes)
        if doc_nodes
        else len({n.get("document") for n in chunk_nodes if n.get("document")})
    )

    return {
        "organization": {
            "id": str(organization["id"]),
            "name": organization["name"],
            "description": organization["description"],
        },
        "statistics": {
            "nodes": stats.get("nodes", len(graph_data["nodes"])),
            "edges": stats.get("edges", len(graph_data["edges"])),
            "documents": documents_count,
            "chunks": stats.get("chunks", len(chunk_nodes)),
            "chunks_with_embedding": stats.get("chunks_with_embedding", 0),
            "chunks_without_embedding": stats.get("chunks_without_embedding", 0),
            "similarity_threshold": stats.get(
                "similarity_threshold", similarity_threshold
            ),
            "average_similarity": stats.get("average_similarity", 0),
            "knowledge_base_id": kb_id,
        },
        "graph": graph_data,
    }
