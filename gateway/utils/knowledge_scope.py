from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


ADMIN_ROLES = {"admin", "super_admin", "org_admin"}


@dataclass(frozen=True)
class KnowledgeScope:
    organization_id: str
    tenant_id: str
    department_ids: tuple[str, ...]
    is_admin: bool


async def resolve_knowledge_scope(
    db: AsyncSession,
    *,
    user_id: Any,
    organization_id: Any,
    department_id: str | None = None,
) -> KnowledgeScope:
    membership = (
        (
            await db.execute(
                text(
                    """
                    SELECT om.organization_id::text AS organization_id,
                           t.id::text AS tenant_id,
                           lower(COALESCE(r.name, '')) AS role_name,
                           om.department_id::text AS legacy_department_id
                    FROM organization_members om
                    JOIN tenants t
                      ON t.organization_id=om.organization_id AND t.active=true
                    LEFT JOIN roles r ON r.id=om.role_id
                    WHERE om.user_id=:user
                      AND om.organization_id=:organization
                      AND om.active=true
                    LIMIT 1
                    """
                ),
                {"user": user_id, "organization": organization_id},
            )
        )
        .mappings()
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=403,
            detail="No perteneces a esta organización o no tiene tenant activo.",
        )

    rows = (
        await db.execute(
            text(
                """
                SELECT DISTINCT dm.department_id::text
                FROM department_members dm
                JOIN departments d ON d.id=dm.department_id
                WHERE dm.user_id=:user AND d.organization_id=:organization
                """
            ),
            {"user": user_id, "organization": organization_id},
        )
    ).all()
    departments = {str(row[0]) for row in rows if row[0]}
    legacy = membership.get("legacy_department_id")
    if legacy:
        departments.add(str(legacy))

    is_admin = str(membership.get("role_name") or "") in ADMIN_ROLES
    if department_id:
        valid = await db.scalar(
            text(
                "SELECT 1 FROM departments "
                "WHERE id=:department AND organization_id=:organization"
            ),
            {"department": department_id, "organization": organization_id},
        )
        if not valid:
            raise HTTPException(status_code=404, detail="Departamento no encontrado.")
        if not is_admin and department_id not in departments:
            raise HTTPException(
                status_code=403,
                detail="No perteneces al departamento seleccionado.",
            )
        departments = {department_id}
    elif is_admin:
        departments = set()
    elif not departments:
        raise HTTPException(
            status_code=403,
            detail="El usuario no tiene un departamento asignado.",
        )

    return KnowledgeScope(
        organization_id=str(membership["organization_id"]),
        tenant_id=str(membership["tenant_id"]),
        department_ids=tuple(sorted(departments)),
        is_admin=is_admin,
    )


async def resolve_knowledge_collections(
    db: AsyncSession,
    *,
    scope: KnowledgeScope,
    knowledge_base_id: str | None = None,
) -> list[str] | None:
    if knowledge_base_id:
        exists = await db.scalar(
            text(
                """
                SELECT 1 FROM knowledge_bases kb
                WHERE kb.id=:kb AND kb.tenant_id=:tenant
                  AND (
                    CAST(:filter_departments AS boolean)=false
                    OR EXISTS (
                      SELECT 1 FROM department_knowledge_bases dkb
                      WHERE dkb.knowledge_base_id=kb.id
                        AND dkb.department_id::text = ANY(:departments)
                    )
                  )
                """
            ),
            {
                "kb": knowledge_base_id,
                "tenant": scope.tenant_id,
                "filter_departments": bool(scope.department_ids),
                "departments": list(scope.department_ids),
            },
        )
        if not exists:
            raise HTTPException(
                status_code=403,
                detail="La base de conocimiento no pertenece al ámbito seleccionado.",
            )
        return [str(knowledge_base_id)]

    if not scope.department_ids:
        return None
    rows = (
        await db.execute(
            text(
                """
                SELECT DISTINCT dkb.knowledge_base_id::text
                FROM department_knowledge_bases dkb
                JOIN knowledge_bases kb ON kb.id=dkb.knowledge_base_id
                WHERE kb.tenant_id=:tenant
                  AND dkb.department_id::text = ANY(:departments)
                ORDER BY dkb.knowledge_base_id::text
                """
            ),
            {
                "tenant": scope.tenant_id,
                "departments": list(scope.department_ids),
            },
        )
    ).all()
    collections = [str(row[0]) for row in rows if row[0]]
    if not collections:
        raise HTTPException(
            status_code=404,
            detail="El departamento no tiene bases de conocimiento asociadas.",
        )
    return collections
