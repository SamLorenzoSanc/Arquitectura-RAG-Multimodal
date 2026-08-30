from identity.http import get_current_user, http_error
from tenancy.postgres import build_tenancy_container
from core.exceptions import AppError
from schemas.catalog import OrganizationCreateRequest
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from services.database import get_db

organization_router = APIRouter(prefix="/organization", tags=["Organization"])


def get_tenancy(db: AsyncSession = Depends(get_db)):
    return build_tenancy_container(db)


@organization_router.post("", status_code=201)
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


@organization_router.get("", status_code=200)
async def list_organizations(
    current_user: User = Depends(get_current_user), hexagon=Depends(get_tenancy)
):
    return await hexagon.repo.list_organizations(current_user.id)


@organization_router.get("/{organization_id}")
async def get_organization(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    try:
        return await hexagon.repo.get_organization(organization_id, current_user.id)
    except AppError as exc:
        raise http_error(exc) from exc


@organization_router.patch("/{organization_id}/deactivate")
async def deactivate_organization(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    return await hexagon.repo.set_active(organization_id, current_user.id, False)


@organization_router.patch("/{organization_id}/activate")
async def activate_organization(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    return await hexagon.repo.set_active(organization_id, current_user.id, True)


@organization_router.delete("/{organization_id}")
async def delete_organization(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    return await hexagon.repo.delete_organization(organization_id, current_user.id)


@organization_router.get("/{organization_id}/members")
async def get_members(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    try:
        return await hexagon.repo.members(organization_id, current_user.id)
    except AppError as exc:
        raise http_error(exc) from exc


@organization_router.get("/{organization_id}/departments", status_code=200)
async def get_departments(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    return await hexagon.repo.departments(organization_id, current_user.id)


@organization_router.get("/{organization_id}/knowledge-bases", status_code=200)
async def list_organization_knowledge_bases(
    organization_id: UUID,
    department_id: UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    return await hexagon.repo.knowledge_bases(
        organization_id, department_id, current_user.id
    )


@organization_router.get("/{organization_id}/knowledge-map")
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

from schemas.catalog import (
    AddMemberPayload,
    DepartmentCreateRequest,
    DepartmentUpdateRequest,
)
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from services.database import get_db

department_router = APIRouter(prefix="/department", tags=["Department"])




@department_router.post("")
async def create_department(
    request: DepartmentCreateRequest,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    department = (
        (
            await hexagon.repo.execute(
                """
                INSERT INTO departments(organization_id, name, description)
                VALUES(:organization_id, :name, :description)
                RETURNING id, organization_id, name, description
                """,
                request.model_dump(),
            )
        )
        .mappings()
        .first()
    )
    await hexagon.repo.commit()
    return department


@department_router.get("/organization/{organization_id}")
async def list_departments(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    return await hexagon.repo.mappings_all(
        """
                SELECT d.id, d.name, d.description, COUNT(dm.user_id) AS members
                FROM departments d
                LEFT JOIN department_members dm ON dm.department_id=d.id
                WHERE d.organization_id=:organization_id
                GROUP BY d.id, d.name, d.description
                ORDER BY d.name
                """,
        {"organization_id": organization_id},
    )


@department_router.get("/{department_id}")
async def get_department(
    department_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    department = await hexagon.repo.mappings_first(
        """
                SELECT id, organization_id, name, description
                FROM departments WHERE id=:id
                """,
        {"id": department_id},
    )
    if not department:
        raise http_error(AppError("Departamento no encontrado", 404))
    return department


@department_router.put("/{department_id}")
async def update_department(
    department_id: str,
    request: DepartmentUpdateRequest,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    await hexagon.repo.execute(
        """
            UPDATE departments SET name=:name, description=:description WHERE id=:id
            """,
        {"id": department_id, **request.model_dump()},
    )
    await hexagon.repo.commit()
    return {"status": "updated"}


@department_router.delete("/{department_id}")
async def delete_department(
    department_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    await hexagon.repo.execute("DELETE FROM departments WHERE id=:id", {"id": department_id})
    await hexagon.repo.commit()
    return {"status": "deleted"}


@department_router.get("/{department_id}/members")
async def list_department_members(
    department_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    members = await hexagon.repo.mappings_all(
        """
                SELECT u.id, u.name, u.email
                FROM department_members dm
                JOIN users u ON u.id = dm.user_id
                WHERE dm.department_id=:department_id
                ORDER BY u.name
                """,
        {"department_id": department_id},
    )
    return {"items": members, "total": len(members)}


@department_router.post("/{department_id}/members")
async def add_department_member(
    department_id: str,
    request: AddMemberPayload,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    user_id = await hexagon.repo.scalar(
        "SELECT id FROM users WHERE email = :email AND active = true",
        {"email": request.email.strip().lower()},
    )
    if user_id is None:
        user_id = await hexagon.repo.scalar(
            "SELECT id FROM users WHERE lower(email) = lower(:email) AND active = true",
            {"email": request.email.strip()},
        )
    if user_id is None:
        raise http_error(
            AppError(
                f"No existe un usuario activo con el email '{request.email}'.", 404
            )
        )
    dept = await hexagon.repo.mappings_first(
        "SELECT id, organization_id FROM departments WHERE id = :id",
        {"id": department_id},
    )
    if dept is None:
        raise http_error(AppError("Departamento no encontrado", 404))
    await hexagon.repo.execute(
        """
            INSERT INTO organization_members (organization_id, user_id, role_id, active)
            VALUES (:org_id, :user_id, :role_id, true)
            ON CONFLICT (organization_id, user_id) DO UPDATE
            SET role_id = COALESCE(EXCLUDED.role_id, organization_members.role_id),
                active = true
            """,
        {
            "org_id": dept["organization_id"],
            "user_id": user_id,
            "role_id": request.role_id,
        },
    )
    await hexagon.repo.execute(
        """
            INSERT INTO department_members (department_id, user_id, role_id)
            VALUES (:department_id, :user_id, :role_id)
            ON CONFLICT (department_id, user_id)
            DO UPDATE SET role_id = COALESCE(EXCLUDED.role_id, department_members.role_id)
            """,
        {
            "department_id": department_id,
            "user_id": user_id,
            "role_id": request.role_id,
        },
    )
    await hexagon.repo.commit()
    return {
        "status": "member_added",
        "user_id": str(user_id),
        "email": request.email,
        "role_id": request.role_id,
    }


@department_router.delete("/{department_id}/members/{user_id}")
async def remove_department_member(
    department_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    await hexagon.repo.execute(
        """
            DELETE FROM department_members
            WHERE department_id=:department_id AND user_id=:user_id
            """,
        {"department_id": department_id, "user_id": user_id},
    )
    await hexagon.repo.commit()
    return {"status": "member_removed"}


@department_router.get("/user/{user_id}")
async def get_user_departments(
    user_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    departments = await hexagon.repo.mappings_all(
        """
                SELECT d.id, d.name, d.description
                FROM department_members dm
                JOIN departments d ON d.id = dm.department_id
                WHERE dm.user_id=:user_id
                ORDER BY d.name
                """,
        {"user_id": user_id},
    )
    return {"items": departments, "total": len(departments)}


@department_router.get("/{department_id}/available-users")
async def available_users(
    department_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    users = await hexagon.repo.mappings_all(
        """
                SELECT u.id, u.name, u.email
                FROM users u
                WHERE NOT EXISTS (
                    SELECT 1 FROM department_members dm
                    WHERE dm.department_id=:department_id AND dm.user_id=u.id
                )
                ORDER BY u.name
                """,
        {"department_id": department_id},
    )
    return {"items": users, "total": len(users)}

from schemas.catalog import KnowledgeBaseCreate, KnowledgeBaseUpdate
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from services.rag_service import RAGService
from services.database import get_db

knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])




@knowledge_router.post("/", status_code=status.HTTP_201_CREATED)
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


@knowledge_router.get("/")
async def list_knowledge_bases(
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
    organization_id: UUID | None = Query(None),
):
    return await hexagon.repo.list_knowledge_bases_for_user(
        current_user.id, organization_id
    )


@knowledge_router.get("/current")
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


@knowledge_router.get("/{knowledge_base_id}")
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


@knowledge_router.patch("/{knowledge_base_id}")
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


@knowledge_router.delete("/{knowledge_base_id}")
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

from schemas.common import AssignTenantRequest, TenantCreate, TenantUpdate
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from services.database import get_db

tenant_router = APIRouter(prefix="/tenants", tags=["Tenants"])




@tenant_router.get("/")
async def list_tenants(
    current_user: User = Depends(get_current_user), hexagon=Depends(get_tenancy)
):
    return await hexagon.repo.list_tenants()


@tenant_router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    try:
        return await hexagon.repo.get_tenant(tenant_id)
    except AppError as exc:
        raise http_error(exc) from exc


@tenant_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant: TenantCreate,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    try:
        return await hexagon.repo.create_tenant(tenant.name, tenant.description)
    except AppError as exc:
        raise http_error(exc) from exc


@tenant_router.put("/{tenant_id}")
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


@tenant_router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    try:
        await hexagon.repo.delete_tenant(tenant_id)
    except AppError as exc:
        raise http_error(exc) from exc


@tenant_router.post("/assign")
async def assign_tenant_to_user(
    data: AssignTenantRequest,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    try:
        return await hexagon.repo.assign_tenant(data.tenant_id, data.user_id)
    except AppError as exc:
        raise http_error(exc) from exc
