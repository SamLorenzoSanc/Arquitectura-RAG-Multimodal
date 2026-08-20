from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from identity.adapters.inbound.auth import get_current_user
from identity.adapters.inbound.errors import http_error
from models.user import User
from schemas.department import (
    AddMemberPayload,
    DepartmentCreateRequest,
    DepartmentUpdateRequest,
)
from services.database import get_db
from shared.errors import AppError
from tenancy.composition import build_tenancy_container

router = APIRouter(prefix="/department", tags=["Department"])


def get_tenancy(db: AsyncSession = Depends(get_db)):
    return build_tenancy_container(db)


@router.post("")
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


@router.get("/organization/{organization_id}")
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


@router.get("/{department_id}")
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


@router.put("/{department_id}")
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


@router.delete("/{department_id}")
async def delete_department(
    department_id: str,
    current_user: User = Depends(get_current_user),
    hexagon=Depends(get_tenancy),
):
    await hexagon.repo.execute("DELETE FROM departments WHERE id=:id", {"id": department_id})
    await hexagon.repo.commit()
    return {"status": "deleted"}


@router.get("/{department_id}/members")
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


@router.post("/{department_id}/members")
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


@router.delete("/{department_id}/members/{user_id}")
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


@router.get("/user/{user_id}")
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


@router.get("/{department_id}/available-users")
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
