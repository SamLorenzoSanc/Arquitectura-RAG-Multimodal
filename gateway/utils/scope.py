from __future__ import annotations

"""Organización global compartida (AgroTech) para todos los usuarios."""

from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

GLOBAL_ORG_NAME = "AgroTech"


async def _resolve_member_role_id(db: AsyncSession):
    """Rol para miembros de AgroTech: USER → MEMBER → ORG_ADMIN (global)."""
    for role_name in ("USER", "MEMBER", "ORG_ADMIN"):
        role_id = await db.scalar(
            text(
                """
                SELECT id FROM roles
                WHERE name = :name AND organization_id IS NULL
                LIMIT 1
                """
            ),
            {"name": role_name},
        )
        if role_id:
            return role_id
    return await db.scalar(
        text("SELECT id FROM roles WHERE organization_id IS NULL ORDER BY id LIMIT 1")
    )


async def ensure_global_organization(db: AsyncSession) -> str | None:
    """Crea AgroTech (+ tenant + KB) si no existe. Devuelve organization_id."""
    existing = await db.scalar(
        text(
            """
            SELECT id FROM organizations
            WHERE lower(name) = lower(:name)
            LIMIT 1
            """
        ),
        {"name": GLOBAL_ORG_NAME},
    )
    if existing:
        # Reactivar si estuviera inactiva
        await db.execute(
            text(
                """
                UPDATE organizations SET active = true
                WHERE id = :id AND active = false
                """
            ),
            {"id": existing},
        )
        return str(existing)

    org_id = str(uuid4())
    await db.execute(
        text(
            """
            INSERT INTO organizations (id, name, description, active)
            VALUES (:id, :name, :description, true)
            """
        ),
        {
            "id": org_id,
            "name": GLOBAL_ORG_NAME,
            "description": "Organización global compartida (base de conocimiento de referencia)",
        },
    )

    tenant_id = str(uuid4())
    await db.execute(
        text(
            """
            INSERT INTO tenants (id, organization_id, name, description, active)
            VALUES (:id, :organization_id, :name, :description, true)
            """
        ),
        {
            "id": tenant_id,
            "organization_id": org_id,
            "name": "Default",
            "description": "Tenant AgroTech",
        },
    )

    kb_id = str(uuid4())
    await db.execute(
        text(
            """
            INSERT INTO knowledge_bases (id, tenant_id, name, description, chroma_collection)
            VALUES (:id, :tenant_id, :name, :description, :chroma_collection)
            """
        ),
        {
            "id": kb_id,
            "tenant_id": tenant_id,
            "name": "General",
            "description": "Knowledge Base global AgroTech",
            "chroma_collection": f"col_{tenant_id.replace('-', '')}",
        },
    )
    return org_id


async def ensure_agrotech_membership(db: AsyncSession, user_id) -> str | None:
    """
    Garantiza que el usuario es miembro activo de AgroTech.
    Todos los usuarios nuevos (y existentes al listar/login) la ven
    además de su organización personal.
    """
    org_id = await ensure_global_organization(db)
    if not org_id:
        return None

    role_id = await _resolve_member_role_id(db)
    if not role_id:
        return org_id

    await db.execute(
        text(
            """
            INSERT INTO organization_members (organization_id, user_id, role_id, active)
            VALUES (:org_id, :user_id, :role_id, true)
            ON CONFLICT (organization_id, user_id) DO UPDATE
            SET active = true,
                role_id = COALESCE(organization_members.role_id, EXCLUDED.role_id)
            """
        ),
        {"org_id": org_id, "user_id": user_id, "role_id": role_id},
    )
    return org_id


# utils/tenant.py
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models import OrganizationMember, Tenant


async def get_tenant_id_for_organization(
    user_id: UUID | str,
    organization_id: UUID | str,
    db: AsyncSession,
) -> str:
    """Tenant activo de una organización concreta, si el usuario es miembro."""
    query = (
        select(Tenant.id)
        .join(
            OrganizationMember,
            OrganizationMember.organization_id == Tenant.organization_id,
        )
        .where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.active.is_(True),
            Tenant.active.is_(True),
        )
        .limit(1)
    )
    result = await db.execute(query)
    tenant_id = result.scalar_one_or_none()

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "El usuario no pertenece a esta organización "
                "o no tiene tenant activo."
            ),
        )

    return str(tenant_id)


async def get_user_tenant_id(
    user_id: UUID | str,
    db: AsyncSession,
    organization_id: UUID | str | None = None,
) -> str:
    """
    Tenant del usuario.

    Si se pasa organization_id, resuelve ese tenant (multitenant correcto).
    Si no, prioriza AgroTech y luego cualquier membership activa.
    """
    if organization_id:
        return await get_tenant_id_for_organization(user_id, organization_id, db)

    # Preferir org global AgroTech cuando hay varias memberships
    
    preferred = await db.scalar(
        text("""
            SELECT t.id
            FROM organization_members om
            JOIN tenants t ON t.organization_id = om.organization_id
            JOIN organizations o ON o.id = om.organization_id
            WHERE om.user_id = :user_id
              AND om.active = true
              AND t.active = true
              AND o.active = true
            ORDER BY CASE WHEN lower(o.name) = lower(:global_name) THEN 0 ELSE 1 END,
                     o.name
            LIMIT 1
        """),
        {"user_id": user_id, "global_name": GLOBAL_ORG_NAME},
    )
    if preferred:
        return str(preferred)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User does not belong to an active organization with an assigned tenant.",
    )



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
