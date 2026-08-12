from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db
from routes.auth import get_current_user
from models.user import User
from schemas.department import (
    DepartmentCreateRequest,
    DepartmentUpdateRequest,
    AddMemberPayload,
)

router = APIRouter(
    prefix="/department",
    tags=["Department"],
)

# ============================================================
# Crear departamento
# ============================================================


@router.post("")
async def create_department(
    request: DepartmentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    department = (
        (
            await db.execute(
                text("""
                INSERT INTO departments(
                    organization_id,
                    name,
                    description
                )
                VALUES(
                    :organization_id,
                    :name,
                    :description
                )
                RETURNING
                    id,
                    organization_id,
                    name,
                    description
                """),
                request.model_dump(),
            )
        )
        .mappings()
        .first()
    )

    await db.commit()

    return department


# ============================================================
# Listar departamentos de una organización
# ============================================================


@router.get("/organization/{organization_id}")
async def list_departments(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    departments = (
        (
            await db.execute(
                text("""
                SELECT
                    d.id,
                    d.name,
                    d.description,
                    COUNT(dm.user_id) AS members
                FROM departments d

                LEFT JOIN department_members dm
                    ON dm.department_id=d.id

                WHERE d.organization_id=:organization_id

                GROUP BY
                    d.id,
                    d.name,
                    d.description

                ORDER BY d.name
                """),
                {"organization_id": organization_id},
            )
        )
        .mappings()
        .all()
    )

    return departments


# ============================================================
# Obtener un departamento
# ============================================================


@router.get("/{department_id}")
async def get_department(
    department_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    department = (
        (
            await db.execute(
                text("""
                SELECT
                    id,
                    organization_id,
                    name,
                    description
                FROM departments
                WHERE id=:id
                """),
                {"id": department_id},
            )
        )
        .mappings()
        .first()
    )

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Departamento no encontrado",
        )

    return department


# ============================================================
# Actualizar departamento
# ============================================================


@router.put("/{department_id}")
async def update_department(
    department_id: str,
    request: DepartmentUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    await db.execute(
        text("""
            UPDATE departments
            SET
                name=:name,
                description=:description
            WHERE id=:id
            """),
        {
            "id": department_id,
            **request.model_dump(),
        },
    )

    await db.commit()

    return {"status": "updated"}


# ============================================================
# Eliminar departamento
# ============================================================


@router.delete("/{department_id}")
async def delete_department(
    department_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    await db.execute(
        text("""
            DELETE
            FROM departments
            WHERE id=:id
            """),
        {"id": department_id},
    )

    await db.commit()

    return {"status": "deleted"}


# ============================================================
# Listar miembros de un departamento
# ============================================================


@router.get("/{department_id}/members")
async def list_department_members(
    department_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    members = (
        (
            await db.execute(
                text("""
                SELECT
                    u.id,
                    u.name,
                    u.email
                FROM department_members dm

                JOIN users u
                    ON u.id = dm.user_id

                WHERE dm.department_id=:department_id

                ORDER BY u.name
                """),
                {"department_id": department_id},
            )
        )
        .mappings()
        .all()
    )

    return {"items": members, "total": len(members)}


# ============================================================
# Añadir usuario a un departamento
# ============================================================


@router.post("/{department_id}/members")
async def add_department_member(
    department_id: str,
    request: AddMemberPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # El frontend envía email (+ role_id opcional); resolvemos a user_id.
    user_id = await db.scalar(
        text("SELECT id FROM users WHERE email = :email AND active = true"),
        {"email": request.email.strip().lower()},
    )
    if user_id is None:
        # Intento case-insensitive por si el email se guardó con mayúsculas.
        user_id = await db.scalar(
            text(
                "SELECT id FROM users WHERE lower(email) = lower(:email) AND active = true"
            ),
            {"email": request.email.strip()},
        )
    if user_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"No existe un usuario activo con el email '{request.email}'.",
        )

    dept = (
        (
            await db.execute(
                text(
                    "SELECT id, organization_id FROM departments WHERE id = :id"
                ),
                {"id": department_id},
            )
        )
        .mappings()
        .first()
    )
    if dept is None:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")

    # Asegurar membresía en la organización del departamento.
    await db.execute(
        text("""
            INSERT INTO organization_members (organization_id, user_id, role_id, active)
            VALUES (:org_id, :user_id, :role_id, true)
            ON CONFLICT (organization_id, user_id) DO UPDATE
            SET
                role_id = COALESCE(EXCLUDED.role_id, organization_members.role_id),
                active = true
            """),
        {
            "org_id": dept["organization_id"],
            "user_id": user_id,
            "role_id": request.role_id,
        },
    )

    await db.execute(
        text("""
            INSERT INTO department_members (
                department_id,
                user_id,
                role_id
            )
            VALUES (
                :department_id,
                :user_id,
                :role_id
            )
            ON CONFLICT (department_id, user_id)
            DO UPDATE SET role_id = COALESCE(EXCLUDED.role_id, department_members.role_id)
            """),
        {
            "department_id": department_id,
            "user_id": user_id,
            "role_id": request.role_id,
        },
    )

    await db.commit()

    return {
        "status": "member_added",
        "user_id": str(user_id),
        "email": request.email,
        "role_id": request.role_id,
    }


# ============================================================
# Eliminar usuario de un departamento
# ============================================================


@router.delete("/{department_id}/members/{user_id}")
async def remove_department_member(
    department_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    await db.execute(
        text("""
            DELETE
            FROM department_members
            WHERE
                department_id=:department_id
            AND
                user_id=:user_id
            """),
        {
            "department_id": department_id,
            "user_id": user_id,
        },
    )

    await db.commit()

    return {"status": "member_removed"}


# ============================================================
# Departamentos de un usuario
# ============================================================


@router.get("/user/{user_id}")
async def get_user_departments(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    departments = (
        (
            await db.execute(
                text("""
                SELECT
                    d.id,
                    d.name,
                    d.description
                FROM department_members dm

                JOIN departments d
                    ON d.id = dm.department_id

                WHERE dm.user_id=:user_id

                ORDER BY d.name
                """),
                {"user_id": user_id},
            )
        )
        .mappings()
        .all()
    )

    return {"items": departments, "total": len(departments)}


# ============================================================
# Usuarios disponibles para añadir
# ============================================================


@router.get("/{department_id}/available-users")
async def available_users(
    department_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    users = (
        (
            await db.execute(
                text("""
                SELECT
                    u.id,
                    u.name,
                    u.email
                FROM users u

                WHERE NOT EXISTS (
                    SELECT 1
                    FROM department_members dm
                    WHERE
                        dm.department_id=:department_id
                    AND
                        dm.user_id=u.id
                )

                ORDER BY u.name
                """),
                {"department_id": department_id},
            )
        )
        .mappings()
        .all()
    )

    return {"items": users, "total": len(users)}
