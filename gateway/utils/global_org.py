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
