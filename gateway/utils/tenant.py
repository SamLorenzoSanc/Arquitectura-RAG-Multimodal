# utils/tenants.py
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import OrganizationMember, Tenant


async def get_user_tenant_id(user_id: UUID, db: AsyncSession) -> str:
    """Retrieves the active tenant_id for a user through their organization."""
    query = (
        select(Tenant.id)
        .join(OrganizationMember, OrganizationMember.organization_id == Tenant.organization_id)
        .where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.active.is_(True),
            Tenant.active.is_(True),
        )
    )
    result = await db.execute(query)
    tenant_id = result.scalar_one_or_none()

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to an active organization with an assigned tenant.",
        )

    return str(tenant_id)