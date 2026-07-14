from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db
from schemas.department import (
    DepartmentCreateRequest,
    DepartmentUpdateRequest,
    DepartmentMemberRequest,
)
from routes.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/department", tags=["Department"])


async def ensure_department_members_table(db: AsyncSession) -> None:
    try:
        await db.execute(text("SELECT 1 FROM department_members LIMIT 1"))
    except ProgrammingError as exc:
        if "relation \"department_members\" does not exist" not in str(exc).lower():
            raise

        await db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS department_members (
                    department_id UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (department_id, user_id)
                )
                """
            )
        )
        await db.commit()


# ---------------------------------------------------------
# Obtener todos los departamentos de una organización
# ---------------------------------------------------------

@router.get("/organization/{organization_id}")
async def get_departments(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_department_members_table(db)

    departments = (
        await db.execute(
            text(
                """
                SELECT
                    d.id,
                    d.name,
                    d.description,
                    COUNT(dm.user_id) AS members
                FROM departments d
                LEFT JOIN department_members dm
                    ON dm.department_id = d.id
                WHERE d.organization_id = :organization_id
                GROUP BY d.id
                ORDER BY d.name
                """
            ),
            {"organization_id": organization_id},
        )
    ).mappings().all()

    return departments


# ---------------------------------------------------------
# Obtener un departamento
# ---------------------------------------------------------

@router.get("/{department_id}")
async def get_department(
    department_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    department = (
        await db.execute(
            text(
                """
                SELECT
                    id,
                    organization_id,
                    name,
                    description
                FROM departments
                WHERE id = :id
                """
            ),
            {"id": department_id},
        )
    ).mappings().first()

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Departamento no encontrado",
        )

    return department


# ---------------------------------------------------------
# Crear departamento
# ---------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_department(
    request: DepartmentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    exists = await db.scalar(
        text(
            """
            SELECT id
            FROM departments
            WHERE organization_id=:organization_id
            AND name=:name
            """
        ),
        {
            "organization_id": request.organization_id,
            "name": request.name,
        },
    )

    if exists:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un departamento con ese nombre.",
        )

    department_id = await db.scalar(
        text(
            """
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
            RETURNING id
            """
        ),
        request.model_dump(),
    )

    await db.commit()

    return {
        "status": "success",
        "department_id": str(department_id),
    }


# ---------------------------------------------------------
# Actualizar departamento
# ---------------------------------------------------------

@router.put("/{department_id}")
async def update_department(
    department_id: str,
    request: DepartmentUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        text(
            """
            UPDATE departments
            SET
                name=:name,
                description=:description
            WHERE id=:id
            """
        ),
        {
            "id": department_id,
            **request.model_dump(),
        },
    )

    await db.commit()

    return {"status": "updated"}


# ---------------------------------------------------------
# Eliminar departamento
# ---------------------------------------------------------

@router.delete("/{department_id}")
async def delete_department(
    department_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        text(
            """
            DELETE FROM departments
            WHERE id=:id
            """
        ),
        {"id": department_id},
    )

    await db.commit()

    return {"status": "deleted"}


# ---------------------------------------------------------
# Miembros del departamento
# ---------------------------------------------------------

@router.get("/{department_id}/members")
async def get_department_members(
    department_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_department_members_table(db)

    members = (
        await db.execute(
            text(
                """
                SELECT
                    u.id,
                    u.name,
                    u.email
                FROM department_members dm
                JOIN users u
                    ON u.id = dm.user_id
                WHERE dm.department_id=:department_id
                ORDER BY u.name
                """
            ),
            {"department_id": department_id},
        )
    ).mappings().all()

    return members


# ---------------------------------------------------------
# Añadir miembro
# ---------------------------------------------------------

@router.post("/{department_id}/members")
async def add_department_member(
    department_id: str,
    request: DepartmentMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_department_members_table(db)

    exists = await db.scalar(
        text(
            """
            SELECT 1
            FROM department_members
            WHERE department_id=:department_id
            AND user_id=:user_id
            """
        ),
        {
            "department_id": department_id,
            "user_id": request.user_id,
        },
    )

    if exists:
        raise HTTPException(
            status_code=400,
            detail="El usuario ya pertenece al departamento.")

    await db.execute(
        text(
            """
            INSERT INTO department_members(
                department_id,
                user_id
            )
            VALUES(
                :department_id,
                :user_id
            )
            """
        ),
        {
            "department_id": department_id,
            "user_id": request.user_id,
        },
    )

    await db.commit()

    return {"status": "member_added"}


# ---------------------------------------------------------
# Eliminar miembro
# ---------------------------------------------------------

@router.delete("/{department_id}/members/{user_id}")
async def remove_department_member(
    department_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_department_members_table(db)

    await db.execute(
        text(
            """
            DELETE FROM department_members
            WHERE department_id=:department_id
            AND user_id=:user_id
            """
        ),
        {
            "department_id": department_id,
            "user_id": user_id,
        },
    )

    await db.commit()

    return {"status": "member_removed"}