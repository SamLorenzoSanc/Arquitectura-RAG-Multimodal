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
    from utils.global_org import GLOBAL_ORG_NAME

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
