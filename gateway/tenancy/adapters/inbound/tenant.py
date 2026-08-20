from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from identity.adapters.inbound.auth import get_current_user
from identity.adapters.inbound.errors import http_error
from models.user import User
from schemas.tenant import AssignTenantRequest, TenantCreate, TenantUpdate
from services.database import get_db
from shared.errors import AppError
from tenancy.composition import build_tenancy_container

router = APIRouter(prefix="/tenants", tags=["Tenants"])


def get_tenancy(db: AsyncSession = Depends(get_db)):
    return build_tenancy_container(db)


@router.get("/")
async def list_tenants(
    current_user: User = Depends(get_current_user), hexagon=Depends(get_tenancy)
):
    return await hexagon.repo.list_tenants()


@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    try:
        return await hexagon.repo.get_tenant(tenant_id)
    except AppError as exc:
        raise http_error(exc) from exc


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant: TenantCreate,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    try:
        return await hexagon.repo.create_tenant(tenant.name, tenant.description)
    except AppError as exc:
        raise http_error(exc) from exc


@router.put("/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    tenant: TenantUpdate,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    try:
        return await hexagon.repo.update_tenant(
            tenant_id, tenant.name, tenant.description, tenant.active
        )
    except AppError as exc:
        raise http_error(exc) from exc


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    try:
        await hexagon.repo.delete_tenant(tenant_id)
    except AppError as exc:
        raise http_error(exc) from exc


@router.post("/assign")
async def assign_tenant_to_user(
    data: AssignTenantRequest,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    try:
        return await hexagon.repo.assign_tenant(data.tenant_id, data.user_id)
    except AppError as exc:
        raise http_error(exc) from exc
