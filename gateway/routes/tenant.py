from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from schemas.tenant import (TenantCreate, TenantUpdate, AssignTenantRequest)
from services.database import get_db
from .auth import get_current_user

router = APIRouter(prefix="/tenants", tags=["Tenants"])


# ==========================================================
# LISTAR
# ==========================================================

@router.get("/")
async def list_tenants(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    tenants = (
        await db.execute(
            text(
                """
                SELECT
                    id,
                    organization_id,
                    name,
                    description,
                    slug,
                    active,
                    created_at,
                    updated_at
                FROM tenants
                ORDER BY created_at DESC
                """
            )
        )
    ).mappings().all()

    return {
        "items": tenants,
        "total": len(tenants),
    }


# ==========================================================
# OBTENER
# ==========================================================

@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    tenant = (
        await db.execute(
            text(
                """
                SELECT
                    id,
                    organization_id,
                    name,
                    description,
                    slug,
                    active,
                    created_at,
                    updated_at
                FROM tenants
                WHERE id=:id
                """
            ),
            {"id": tenant_id},
        )
    ).mappings().first()

    if tenant is None:
        raise HTTPException(
            status_code=404,
            detail="Tenant not found",
        )

    return tenant

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant: TenantCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    organization_id = await db.scalar(
        text("SELECT id FROM organizations LIMIT 1")
    )

    if organization_id is None:
        raise HTTPException(
            status_code=400,
            detail="No organization found.",
        )

    tenant_id = str(uuid4())

    try:

        await db.execute(
            text(
                """
                INSERT INTO tenants (
                    id,
                    organization_id,
                    name,
                    description,
                    created_at,
                    updated_at
                )
                VALUES (
                    :id,
                    :organization_id,
                    :name,
                    :description,
                    NOW(),
                    NOW()
                )
                """
            ),
            {
                "id": tenant_id,
                "organization_id": organization_id,
                "name": tenant.name,
                "description": tenant.description,
            },
        )

        await db.commit()

        created = (
            await db.execute(
                text(
                    """
                    SELECT
                        id,
                        organization_id,
                        name,
                        description,
                        slug,
                        active,
                        created_at,
                        updated_at
                    FROM tenants
                    WHERE id=:id
                    """
                ),
                {"id": tenant_id},
            )
        ).mappings().first()

        return created

    except Exception as e:

        await db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

@router.put("/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    tenant: TenantUpdate,
    current_user: User =Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    exists = await db.scalar(
        text("SELECT id FROM tenants WHERE id=:id"),
        {"id": tenant_id},
    )

    if exists is None:
        raise HTTPException(
            status_code=404,
            detail="Tenant not found",
        )

    await db.execute(
        text(
            """
            UPDATE tenants
            SET
                name=COALESCE(:name,name),
                description=COALESCE(:description,description),
                active=COALESCE(:active,active),
                updated_at=NOW()
            WHERE id=:id
            """
        ),
        {
            "id": tenant_id,
            "name": tenant.name,
            "description": tenant.description,
            "active": tenant.active,
        },
    )

    await db.commit()

    updated = (
        await db.execute(
            text(
                """
                SELECT
                    id,
                    organization_id,
                    name,
                    description,
                    slug,
                    active,
                    created_at,
                    updated_at
                FROM tenants
                WHERE id=:id
                """
            ),
            {"id": tenant_id},
        )
    ).mappings().first()

    return updated

@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    exists = await db.scalar(
        text("SELECT id FROM tenants WHERE id=:id"),
        {"id": tenant_id},
    )

    if exists is None:
        raise HTTPException(
            status_code=404,
            detail="Tenant not found",
        )

    await db.execute(
        text(
            "DELETE FROM tenants WHERE id=:id"
        ),
        {"id": tenant_id},
    )

    await db.commit()


@router.post("/assign")
async def assign_tenant_to_user(
    data: AssignTenantRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    organization_id = await db.scalar(
        text(
            """
            SELECT organization_id
            FROM tenants
            WHERE id=:id
            """
        ),
        {"id": data.tenant_id},
    )

    if organization_id is None:
        raise HTTPException(
            status_code=404,
            detail="Tenant not found",
        )

    user_exists = await db.scalar(
        text(
            "SELECT id FROM users WHERE id=:id"
        ),
        {"id": data.user_id},
    )

    if user_exists is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    await db.execute(
        text(
            """
            INSERT INTO organization_members (
                organization_id,
                user_id,
                active
            )
            VALUES (
                :organization_id,
                :user_id,
                TRUE
            )
            ON CONFLICT (organization_id,user_id)
            DO UPDATE
            SET active=TRUE
            """
        ),
        {
            "organization_id": organization_id,
            "user_id": data.user_id,
        },
    )

    await db.commit()

    return {
        "status": "success",
        "message": "User assigned successfully.",
    }