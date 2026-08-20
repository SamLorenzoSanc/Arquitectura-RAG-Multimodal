from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.knowledge_graph_service import KnowledgeGraphService
from shared.errors import AppError
from utils.global_org import GLOBAL_ORG_NAME, ensure_agrotech_membership
from utils.knowledge_scope import resolve_knowledge_collections, resolve_knowledge_scope
from utils.tenant import get_user_tenant_id
from uuid import UUID, uuid4


class PostgresTenancyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def setup_organization(self, name: str, description, user_id) -> dict:
        exists = await self.db.scalar(
            text("SELECT id FROM organizations WHERE name = :name"),
            {"name": name},
        )
        if exists:
            raise AppError("Ya existe una organización registrada con este nombre", 400)
        org_id = await self.db.scalar(
            text("""
            INSERT INTO organizations (name, description, active)
            VALUES (:name, :description, true)
            RETURNING id
            """),
            {"name": name, "description": description},
        )
        role_id = await self.db.scalar(
            text(
                "SELECT id FROM roles WHERE name = 'ORG_ADMIN' AND organization_id IS NULL LIMIT 1"
            )
        )
        if not role_id:
            raise AppError("Error crítico: Rol ORG_ADMIN global no encontrado.", 500)
        await self.db.execute(
            text("""
            INSERT INTO organization_members (organization_id, user_id, role_id, active)
            VALUES (:org_id, :user_id, :role_id, true)
            """),
            {"org_id": org_id, "user_id": user_id, "role_id": role_id},
        )
        tenant_id = await self.db.scalar(
            text("""
            INSERT INTO tenants (organization_id, name, description, active)
            VALUES (:org_id, 'Tenant Predeterminado', 'Instancia por defecto de la organización', true)
            RETURNING id
            """),
            {"org_id": org_id},
        )
        chroma_collection_name = f"col_{str(tenant_id).replace('-', '')}"
        kb_id = await self.db.scalar(
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
                "user_id": user_id,
            },
        )
        await self.db.commit()
        return {
            "status": "success",
            "message": "Estructura multi-tenant y Base de Conocimiento inicializadas correctamente.",
            "organization_id": str(org_id),
            "tenant_id": str(tenant_id),
            "default_knowledge_base_id": str(kb_id),
        }

    async def ensure_global(self, user_id) -> None:
        await ensure_agrotech_membership(self.db, user_id)
        await self.db.commit()

    async def list_organizations(self, user_id):
        await self.ensure_global(user_id)
        result = await self.db.execute(
            text("""
            SELECT
                o.id, o.name, o.description,
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
            {"user_id": user_id, "global_name": GLOBAL_ORG_NAME},
        )
        return result.mappings().all()

    async def get_organization(self, organization_id, user_id):
        await self.ensure_global(user_id)
        organization = (
            (
                await self.db.execute(
                    text("""
                SELECT o.id, o.name, o.description, o.active
                FROM organizations o
                LEFT JOIN organization_members om
                    ON o.id = om.organization_id
                   AND om.user_id = :user_id
                   AND om.active = true
                WHERE o.id = :id AND o.active = true
                  AND (om.user_id IS NOT NULL OR lower(o.name) = lower(:global_name))
            """),
                    {
                        "id": organization_id,
                        "user_id": user_id,
                        "global_name": GLOBAL_ORG_NAME,
                    },
                )
            )
            .mappings()
            .first()
        )
        if not organization:
            raise AppError("Organización no encontrada o acceso denegado", 404)
        return organization

    async def set_active(self, organization_id, user_id, active: bool) -> dict:
        await self.db.execute(
            text("""
            UPDATE organizations SET active=:active
            WHERE id=:id AND EXISTS (
                SELECT 1 FROM organization_members WHERE organization_id = :id AND user_id = :user_id
            )
        """),
            {"id": organization_id, "user_id": user_id, "active": active},
        )
        await self.db.commit()
        return {"status": "activated" if active else "deactivated"}

    async def delete_organization(self, organization_id, user_id) -> dict:
        await self.db.execute(
            text("""
            DELETE FROM organizations
            WHERE id=:id AND EXISTS (
                SELECT 1 FROM organization_members WHERE organization_id = :id AND user_id = :user_id
            )
        """),
            {"id": organization_id, "user_id": user_id},
        )
        await self.db.commit()
        return {"status": "deleted"}

    async def members(self, organization_id, user_id):
        check = await self.db.scalar(
            text(
                "SELECT 1 FROM organization_members WHERE organization_id = :org_id AND user_id = :user_id"
            ),
            {"org_id": organization_id, "user_id": user_id},
        )
        if not check:
            raise AppError("No perteneces a esta organización", 403)
        members = (
            (
                await self.db.execute(
                    text("""
                SELECT u.id, u.name, u.email, r.name AS role
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

    async def departments(self, organization_id, user_id):
        scope = await resolve_knowledge_scope(
            self.db, user_id=user_id, organization_id=organization_id
        )
        result = await self.db.execute(
            text("""
            SELECT id, name, description
            FROM departments
            WHERE organization_id = :org_id
              AND (
                CAST(:filter_departments AS boolean)=false
                OR id::text = ANY(:department_ids)
              )
            ORDER BY name
            """),
            {
                "org_id": organization_id,
                "filter_departments": bool(scope.department_ids),
                "department_ids": list(scope.department_ids),
            },
        )
        return result.mappings().all()

    async def knowledge_bases(self, organization_id, department_id, user_id):
        scope = await resolve_knowledge_scope(
            self.db,
            user_id=user_id,
            organization_id=organization_id,
            department_id=str(department_id) if department_id else None,
        )
        collections = await resolve_knowledge_collections(self.db, scope=scope)
        result = await self.db.execute(
            text("""
            SELECT
                id, tenant_id, name, description, chroma_collection, created_by, created_at,
                COALESCE((
                    SELECT array_agg(dkb.department_id::text ORDER BY dkb.department_id::text)
                    FROM department_knowledge_bases dkb
                    WHERE dkb.knowledge_base_id=knowledge_bases.id
                ), ARRAY[]::text[]) AS department_ids
            FROM knowledge_bases
            WHERE tenant_id = :tenant_id
              AND (
                CAST(:filter_collections AS boolean)=false
                OR id::text = ANY(:collections)
              )
            ORDER BY created_at ASC
            """),
            {
                "tenant_id": scope.tenant_id,
                "filter_collections": collections is not None,
                "collections": collections or [],
            },
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
                "department_ids": list(row["department_ids"] or []),
            }
            for row in rows
        ]

    async def knowledge_map(
        self,
        organization_id,
        user_id,
        preview: bool,
        knowledge_base_id,
        similarity_threshold: float,
        max_neighbors: int,
    ):
        organization = (
            (
                await self.db.execute(
                    text("""
            SELECT o.id, o.name, o.description
            FROM organizations o
            JOIN organization_members om ON o.id = om.organization_id
            WHERE o.id = :id AND o.active = true AND om.user_id = :user_id
        """),
                    {"id": organization_id, "user_id": user_id},
                )
            )
            .mappings()
            .first()
        )
        if not organization:
            raise AppError("Organización no encontrada o acceso denegado", 404)
        tenant_id = await self.db.scalar(
            text("""
            SELECT id FROM tenants
            WHERE organization_id = :org_id AND active = true
            LIMIT 1
        """),
            {"org_id": organization_id},
        )
        if not tenant_id:
            raise AppError("Tenant no encontrado", 404)
        kb_id = str(knowledge_base_id) if knowledge_base_id else None
        if kb_id:
            kb_ok = await self.db.scalar(
                text("""
                SELECT 1 FROM knowledge_bases
                WHERE id = :kb_id AND tenant_id = :tenant_id
                """),
                {"kb_id": kb_id, "tenant_id": tenant_id},
            )
            if not kb_ok:
                raise AppError("Knowledge base no encontrada en esta organización", 404)
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

    async def execute(self, sql: str, params: dict | None = None):
        return await self.db.execute(text(sql), params or {})

    async def scalar(self, sql: str, params: dict | None = None):
        return await self.db.scalar(text(sql), params or {})

    async def commit(self):
        await self.db.commit()

    async def rollback(self):
        await self.db.rollback()

    async def mappings_all(self, sql: str, params: dict | None = None):
        return (await self.execute(sql, params)).mappings().all()

    async def mappings_first(self, sql: str, params: dict | None = None):
        return (await self.execute(sql, params)).mappings().first()

    async def ensure_project_columns(self) -> None:
        await self.execute(
            "ALTER TABLE knowledge_bases ADD COLUMN IF NOT EXISTS use_case VARCHAR(80)"
        )

    def _project_row(self, row) -> dict:
        return {
            "id": str(row["id"]),
            "tenant_id": str(row["tenant_id"]) if row.get("tenant_id") else None,
            "name": row["name"],
            "description": row.get("description"),
            "use_case": row.get("use_case") or "Q/A",
            "chroma_collection": row.get("chroma_collection"),
            "created_by": str(row["created_by"]) if row.get("created_by") else None,
            "created_by_name": row.get("created_by_name"),
            "created_at": row.get("created_at"),
            "document_count": int(row["document_count"] or 0)
            if row.get("document_count") is not None
            else 0,
        }

    TENANT_SELECT = """
    id, organization_id, name, description, active, created_at
"""

    async def list_tenants(self):
        rows = await self.mappings_all(
            f"SELECT {self.TENANT_SELECT} FROM tenants ORDER BY created_at DESC"
        )
        return {"items": rows, "total": len(rows)}

    async def get_tenant(self, tenant_id: str):
        tenant = await self.mappings_first(
            f"SELECT {self.TENANT_SELECT} FROM tenants WHERE id=:id",
            {"id": tenant_id},
        )
        if tenant is None:
            raise AppError("Tenant not found", 404)
        return tenant

    async def create_tenant(self, name: str, description):
        organization_id = await self.scalar("SELECT id FROM organizations LIMIT 1")
        if organization_id is None:
            raise AppError("No organization found.", 400)
        tenant_id = str(uuid4())
        try:
            await self.execute(
                """
                INSERT INTO tenants (id, organization_id, name, description, created_at)
                VALUES (:id, :organization_id, :name, :description, NOW())
                """,
                {
                    "id": tenant_id,
                    "organization_id": organization_id,
                    "name": name,
                    "description": description,
                },
            )
            await self.commit()
            return await self.mappings_first(
                f"SELECT {self.TENANT_SELECT} FROM tenants WHERE id=:id",
                {"id": tenant_id},
            )
        except Exception as exc:
            await self.rollback()
            raise AppError(str(exc), 500) from exc

    async def update_tenant(self, tenant_id: str, name, description, active):
        exists = await self.scalar(
            "SELECT id FROM tenants WHERE id=:id", {"id": tenant_id}
        )
        if exists is None:
            raise AppError("Tenant not found", 404)
        await self.execute(
            """
            UPDATE tenants SET
                name=COALESCE(:name,name),
                description=COALESCE(:description,description),
                active=COALESCE(:active,active)
            WHERE id=:id
            """,
            {
                "id": tenant_id,
                "name": name,
                "description": description,
                "active": active,
            },
        )
        await self.commit()
        return await self.mappings_first(
            f"SELECT {self.TENANT_SELECT} FROM tenants WHERE id=:id",
            {"id": tenant_id},
        )

    async def delete_tenant(self, tenant_id: str) -> None:
        exists = await self.scalar(
            "SELECT id FROM tenants WHERE id=:id", {"id": tenant_id}
        )
        if exists is None:
            raise AppError("Tenant not found", 404)
        await self.execute("DELETE FROM tenants WHERE id=:id", {"id": tenant_id})
        await self.commit()

    async def assign_tenant(self, tenant_id, user_id) -> dict:
        organization_id = await self.scalar(
            "SELECT organization_id FROM tenants WHERE id=:id", {"id": tenant_id}
        )
        if organization_id is None:
            raise AppError("Tenant not found", 404)
        exists = await self.scalar(
            """
            SELECT id FROM organization_members
            WHERE organization_id=:org AND user_id=:user
            """,
            {"org": organization_id, "user": user_id},
        )
        if exists:
            await self.execute(
                "UPDATE organization_members SET active=true WHERE id=:id",
                {"id": exists},
            )
        else:
            await self.execute(
                """
                INSERT INTO organization_members (id, organization_id, user_id, active)
                VALUES (:id, :org, :user, true)
                """,
                {"id": str(uuid4()), "org": organization_id, "user": user_id},
            )
        await self.commit()
        return {"status": "assigned"}

    async def create_knowledge_base(self, kb, user_id, organization_id):
        await self.ensure_project_columns()
        tenant_id = await get_user_tenant_id(
            user_id, self.db, organization_id=organization_id
        )
        kb_id = str(uuid4())
        use_case = (getattr(kb, "use_case", None) or "Q/A").strip() or "Q/A"
        try:
            await self.execute(
                """
            INSERT INTO knowledge_bases (id, tenant_id, name, description, use_case, chroma_collection, created_by, created_at)
            VALUES (:id, :tenant_id, :name, :description, :use_case, :chroma_collection, :created_by, NOW())
            """,
                {
                    "id": kb_id,
                    "tenant_id": tenant_id,
                    "name": kb.name,
                    "description": kb.description,
                    "use_case": use_case,
                    "chroma_collection": f"kb_{kb_id.replace('-', '')}",
                    "created_by": user_id,
                },
            )
            await self.commit()
            return {
                "id": kb_id,
                "knowledge_base_id": kb_id,
                "name": kb.name,
                "description": kb.description,
                "use_case": use_case,
                "tenant_id": str(tenant_id),
                "status": "created",
            }
        except Exception as exc:
            await self.rollback()
            raise AppError(f"Error al crear la Base de Conocimiento: {exc}", 500) from exc

    async def list_knowledge_bases_for_user(self, user_id, organization_id):
        await self.ensure_project_columns()
        tenant_id = await get_user_tenant_id(
            user_id, self.db, organization_id=organization_id
        )
        rows = await self.mappings_all(
            """
            SELECT
                kb.id, kb.tenant_id, kb.name, kb.description, kb.use_case,
                kb.chroma_collection, kb.created_by, kb.created_at,
                u.name AS created_by_name,
                (
                    SELECT COUNT(*) FROM documents d
                    WHERE d.knowledge_base_id = kb.id
                ) AS document_count
            FROM knowledge_bases kb
            LEFT JOIN users u ON u.id = kb.created_by
            WHERE kb.tenant_id = :tenant_id
            ORDER BY kb.created_at DESC
        """,
            {"tenant_id": tenant_id},
        )
        return [self._project_row(row) for row in rows]

    async def current_knowledge_base(self, user_id, organization_id):
        await self.ensure_project_columns()
        tenant_id = await get_user_tenant_id(
            user_id, self.db, organization_id=organization_id
        )
        kb = await self.mappings_first(
            """
            SELECT
                kb.id, kb.tenant_id, kb.name, kb.description, kb.use_case,
                kb.chroma_collection, kb.created_by, kb.created_at,
                u.name AS created_by_name,
                (
                    SELECT COUNT(*) FROM documents d
                    WHERE d.knowledge_base_id = kb.id
                ) AS document_count
            FROM knowledge_bases kb
            LEFT JOIN users u ON u.id = kb.created_by
            WHERE kb.tenant_id = :tenant_id
            ORDER BY kb.created_at ASC
            LIMIT 1
            """,
            {"tenant_id": tenant_id},
        )
        if not kb:
            raise AppError(
                "No existe ninguna Base de Conocimiento para este tenant.", 404
            )
        return self._project_row(kb)

    async def get_knowledge_base(self, knowledge_base_id, user_id, organization_id):
        await self.ensure_project_columns()
        tenant_id = await get_user_tenant_id(
            user_id, self.db, organization_id=organization_id
        )
        kb = await self.mappings_first(
            """
            SELECT
                kb.id, kb.tenant_id, kb.name, kb.description, kb.use_case,
                kb.chroma_collection, kb.created_by, kb.created_at,
                u.name AS created_by_name,
                (
                    SELECT COUNT(*) FROM documents d
                    WHERE d.knowledge_base_id = kb.id
                ) AS document_count
            FROM knowledge_bases kb
            LEFT JOIN users u ON u.id = kb.created_by
            WHERE kb.id = :kb_id AND kb.tenant_id = :tenant_id
            """,
            {"kb_id": knowledge_base_id, "tenant_id": tenant_id},
        )
        if not kb:
            raise AppError(
                "Base de Conocimiento no encontrada o no tienes permisos para verla.",
                404,
            )
        return self._project_row(kb)

    async def _execute_if_table(self, table: str, sql: str, params: dict) -> None:
        exists = await self.scalar("SELECT to_regclass(:name)", {"name": f"public.{table}"})
        if exists:
            await self.execute(sql, params)

    async def update_knowledge_base(self, knowledge_base_id, payload, user_id, organization_id):
        current = await self.get_knowledge_base(
            knowledge_base_id, user_id, organization_id
        )
        name = (getattr(payload, "name", None) or current["name"]).strip()
        if len(name) < 3:
            raise AppError("El nombre del proyecto debe tener al menos 3 caracteres.", 400)
        description = (
            current["description"]
            if getattr(payload, "description", None) is None
            else payload.description
        )
        if getattr(payload, "use_case", None) is None:
            use_case = current.get("use_case") or "Q/A"
        else:
            use_case = (payload.use_case or "Q/A").strip() or "Q/A"
        await self.execute(
            """
            UPDATE knowledge_bases
            SET name = :name, description = :description, use_case = :use_case
            WHERE id = :id
            """,
            {
                "id": knowledge_base_id,
                "name": name,
                "description": description,
                "use_case": use_case,
            },
        )
        await self.commit()
        return await self.get_knowledge_base(
            knowledge_base_id, user_id, organization_id
        )

    async def delete_knowledge_base(self, knowledge_base_id, user_id, organization_id):
        current = await self.get_knowledge_base(
            knowledge_base_id, user_id, organization_id
        )
        params = {"kb": knowledge_base_id}
        await self.execute(
            """
            DELETE FROM embeddings
            WHERE chunk_id IN (
                SELECT c.id FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE d.knowledge_base_id = :kb
            )
            """,
            params,
        )
        await self.execute(
            """
            DELETE FROM chunks
            WHERE document_id IN (SELECT id FROM documents WHERE knowledge_base_id = :kb)
            """,
            params,
        )
        await self._execute_if_table(
            "processing_jobs",
            """
            DELETE FROM processing_jobs
            WHERE document_id IN (SELECT id FROM documents WHERE knowledge_base_id = :kb)
            """,
            params,
        )
        await self._execute_if_table(
            "document_versions",
            """
            DELETE FROM document_versions
            WHERE document_id IN (SELECT id FROM documents WHERE knowledge_base_id = :kb)
            """,
            params,
        )
        await self._execute_if_table(
            "document_tags",
            """
            DELETE FROM document_tags
            WHERE document_id IN (SELECT id FROM documents WHERE knowledge_base_id = :kb)
            """,
            params,
        )
        await self._execute_if_table(
            "document_questions",
            """
            DELETE FROM document_questions
            WHERE document_id IN (SELECT id FROM documents WHERE knowledge_base_id = :kb)
            """,
            params,
        )
        await self._execute_if_table(
            "rag_human_reviews",
            "DELETE FROM rag_human_reviews WHERE knowledge_base_id = :kb",
            params,
        )
        await self.execute(
            "UPDATE conversations SET knowledge_base_id = NULL WHERE knowledge_base_id = :kb",
            params,
        )
        await self._execute_if_table(
            "graph_edges",
            """
            DELETE FROM graph_edges
            WHERE source_node_id IN (SELECT id FROM graph_nodes WHERE knowledge_base_id = :kb)
               OR target_node_id IN (SELECT id FROM graph_nodes WHERE knowledge_base_id = :kb)
            """,
            params,
        )
        await self._execute_if_table(
            "graph_nodes",
            "DELETE FROM graph_nodes WHERE knowledge_base_id = :kb",
            params,
        )
        await self._execute_if_table(
            "knowledge_base_permissions",
            "DELETE FROM knowledge_base_permissions WHERE knowledge_base_id = :kb",
            params,
        )
        await self._execute_if_table(
            "department_knowledge_bases",
            "DELETE FROM department_knowledge_bases WHERE knowledge_base_id = :kb",
            params,
        )
        await self.execute("DELETE FROM documents WHERE knowledge_base_id = :kb", params)
        await self.execute("DELETE FROM knowledge_bases WHERE id = :kb", params)
        await self.commit()
        return {
            "status": "deleted",
            "id": knowledge_base_id,
            "tenant_id": current.get("tenant_id"),
            "name": current.get("name"),
        }

