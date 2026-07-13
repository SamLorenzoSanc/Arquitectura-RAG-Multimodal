from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import uuid4

from schemas.tenant import TenantCreate, AssignTenantRequest
from services.database import get_db
from .auth import get_current_user
from models.user import User

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.get("/")
async def list_tenants(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los tenants accesibles para el usuario."""
    tenants = (
        await db.execute(
            text("""SELECT id, name, description, created_at FROM tenants ORDER BY created_at DESC""")
        )
    ).mappings().all()
    return tenants


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant: TenantCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crea un nuevo Tenant sobre la organización por defecto existente."""
    tenant_id = str(uuid4())
    try:
        organization_id = await db.scalar(
            text("SELECT id FROM organizations LIMIT 1")
        )
        if not organization_id:
            raise HTTPException(
                status_code=400,
                detail="No existe ninguna organización en la BD. Crea una primero.",
            )

        await db.execute(
            text("""
            INSERT INTO tenants (id, organization_id, name, created_at)
            VALUES (:id, :organization_id, :name, NOW())
            """),
            {"id": tenant_id, "organization_id": organization_id, "name": tenant.name},
        )
        await db.commit()

        return {
            "tenant_id": tenant_id,
            "organization_id": str(organization_id),
            "name": tenant.name,
            "status": "created",
        }
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear el Tenant: {e}")


@router.post("/assign")
async def assign_tenant_to_user(
    data: AssignTenantRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Asigna un usuario a la ORGANIZACIÓN dueña del tenant indicado
    (vía organization_members). En este esquema el usuario no cuelga
    de un tenant directamente, sino de la organización.
    """
    # 1. El tenant existe -> obtenemos su organización
    organization_id = await db.scalar(
        text("SELECT organization_id FROM tenants WHERE id = :id"),
        {"id": data.tenant_id},
    )
    if not organization_id:
        raise HTTPException(status_code=404, detail="El Tenant especificado no existe.")

    # 2. El usuario existe
    user_exists = await db.scalar(
        text("SELECT id FROM users WHERE id = :id"), {"id": data.user_id}
    )
    if not user_exists:
        raise HTTPException(status_code=404, detail="El usuario especificado no existe.")

    try:
        # 3. Alta/actualización de la membresía (idempotente gracias al UNIQUE
        #    (organization_id, user_id) de tu esquema)
        await db.execute(
            text("""
            INSERT INTO organization_members (organization_id, user_id, active)
            VALUES (:org_id, :user_id, true)
            ON CONFLICT (organization_id, user_id)
            DO UPDATE SET active = true
            """),
            {"org_id": organization_id, "user_id": data.user_id},
        )
        await db.commit()

        return {
            "status": "success",
            "message": "Usuario asignado a la organización del tenant correctamente.",
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al asignar el Tenant: {e}")