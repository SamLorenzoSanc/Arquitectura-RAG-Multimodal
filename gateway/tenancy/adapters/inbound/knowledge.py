from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from identity.adapters.inbound.auth import get_current_user
from identity.adapters.inbound.errors import http_error
from models.user import User
from schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate
from services.rag_service import RAGService
from services.database import get_db
from shared.errors import AppError
from tenancy.composition import build_tenancy_container

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_tenancy(db: AsyncSession = Depends(get_db)):
    return build_tenancy_container(db)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    kb: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
    organization_id: UUID | None = Query(None),
):
    try:
        return await hexagon.repo.create_knowledge_base(
            kb, current_user.id, organization_id
        )
    except AppError as exc:
        raise http_error(exc) from exc


@router.get("/")
async def list_knowledge_bases(
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
    organization_id: UUID | None = Query(None),
):
    return await hexagon.repo.list_knowledge_bases_for_user(
        current_user.id, organization_id
    )


@router.get("/current")
async def get_current_knowledge_base(
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
    organization_id: UUID | None = Query(None),
):
    try:
        return await hexagon.repo.current_knowledge_base(
            current_user.id, organization_id
        )
    except AppError as exc:
        raise http_error(exc) from exc


@router.get("/{knowledge_base_id}")
async def get_knowledge_base(
    knowledge_base_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
    organization_id: UUID | None = Query(None),
):
    try:
        return await hexagon.repo.get_knowledge_base(
            knowledge_base_id, current_user.id, organization_id
        )
    except AppError as exc:
        raise http_error(exc) from exc


@router.patch("/{knowledge_base_id}")
async def update_knowledge_base(
    knowledge_base_id: str,
    payload: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
    organization_id: UUID | None = Query(None),
):
    try:
        return await hexagon.repo.update_knowledge_base(
            knowledge_base_id, payload, current_user.id, organization_id
        )
    except AppError as exc:
        raise http_error(exc) from exc


@router.delete("/{knowledge_base_id}")
async def delete_knowledge_base(
    knowledge_base_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
    organization_id: UUID | None = Query(None),
):
    try:
        result = await hexagon.repo.delete_knowledge_base(
            knowledge_base_id, current_user.id, organization_id
        )
        tenant_id = result.get("tenant_id")
        if tenant_id:
            RAGService.invalidate_retrieval_cache(str(tenant_id))
        return result
    except AppError as exc:
        raise http_error(exc) from exc
