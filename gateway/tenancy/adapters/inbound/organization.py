from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from identity.adapters.inbound.auth import get_current_user
from identity.adapters.inbound.errors import http_error
from models.user import User
from schemas.organization import OrganizationCreateRequest
from services.database import get_db
from shared.errors import AppError
from tenancy.composition import build_tenancy_container

router = APIRouter(prefix="/organization", tags=["Organization"])


def get_tenancy(db: AsyncSession = Depends(get_db)):
    return build_tenancy_container(db)


@router.post("", status_code=201)
async def setup_organization(
    request: OrganizationCreateRequest,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    try:
        return await hexagon.repo.setup_organization(
            request.name, request.description, current_user.id
        )
    except AppError as exc:
        await hexagon.repo.rollback()
        raise http_error(exc) from exc
    except Exception as exc:
        await hexagon.repo.rollback()
        raise http_error(AppError(f"Error al inicializar la infraestructura: {exc}", 500)) from exc


@router.get("", status_code=200)
async def list_organizations(
    current_user: User = Depends(get_current_user), hexagon=Depends(get_tenancy)
):
    return await hexagon.repo.list_organizations(current_user.id)


@router.get("/{organization_id}")
async def get_organization(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    try:
        return await hexagon.repo.get_organization(organization_id, current_user.id)
    except AppError as exc:
        raise http_error(exc) from exc


@router.patch("/{organization_id}/deactivate")
async def deactivate_organization(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    return await hexagon.repo.set_active(organization_id, current_user.id, False)


@router.patch("/{organization_id}/activate")
async def activate_organization(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    return await hexagon.repo.set_active(organization_id, current_user.id, True)


@router.delete("/{organization_id}")
async def delete_organization(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    return await hexagon.repo.delete_organization(organization_id, current_user.id)


@router.get("/{organization_id}/members")
async def get_members(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    try:
        return await hexagon.repo.members(organization_id, current_user.id)
    except AppError as exc:
        raise http_error(exc) from exc


@router.get("/{organization_id}/departments", status_code=200)
async def get_departments(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    return await hexagon.repo.departments(organization_id, current_user.id)


@router.get("/{organization_id}/knowledge-bases", status_code=200)
async def list_organization_knowledge_bases(
    organization_id: UUID,
    department_id: UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    return await hexagon.repo.knowledge_bases(
        organization_id, department_id, current_user.id
    )


@router.get("/{organization_id}/knowledge-map")
async def graph(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
    preview: bool = False,
    knowledge_base_id: UUID | None = None,
    similarity_threshold: float = 0.45,
    max_neighbors: int = 8,
):
    try:
        return await hexagon.repo.knowledge_map(
            organization_id,
            current_user.id,
            preview,
            knowledge_base_id,
            similarity_threshold,
            max_neighbors,
        )
    except AppError as exc:
        raise http_error(exc) from exc
