from datetime import date, datetime
from typing import Any, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db
from identity.http import get_current_user

router = APIRouter(prefix="/field-notebook", tags=["Field notebook"])

Category = Literal[
    "riego",
    "plaga",
    "fertilizacion",
    "cosecha",
    "clima",
    "maquinaria",
    "otro",
]

ENTRY_COLUMNS = """
    id, user_id, organization_id, crop_id, entry_date, title, body,
    category, reminder_at, created_at, updated_at
"""

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS field_notebook_entries (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    organization_id UUID,
    crop_id VARCHAR(36),
    entry_date DATE NOT NULL,
    title VARCHAR(180) NOT NULL,
    body TEXT,
    category VARCHAR(40) NOT NULL DEFAULT 'otro',
    reminder_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
)
"""


async def init_field_notebook_table(db: AsyncSession) -> None:
    await db.execute(text(CREATE_TABLE_SQL))
    await db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_field_notebook_user_date
            ON field_notebook_entries (user_id, entry_date)
            """
        )
    )
    await db.commit()



class NotebookCreateSchema(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    body: Optional[str] = None
    entry_date: date
    category: Category = "otro"
    crop_id: Optional[str] = None
    organization_id: Optional[str] = None
    reminder_at: Optional[datetime] = None


class NotebookUpdateSchema(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=180)
    body: Optional[str] = None
    entry_date: Optional[date] = None
    category: Optional[Category] = None
    crop_id: Optional[str] = None
    organization_id: Optional[str] = None
    reminder_at: Optional[datetime] = None


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for key in ("id", "user_id", "organization_id", "crop_id"):
        if out.get(key) is not None:
            out[key] = str(out[key])
    for key in ("entry_date", "reminder_at", "created_at", "updated_at"):
        value = out.get(key)
        if value is not None:
            out[key] = value.isoformat()
    return out


@router.get("/", status_code=200)
async def list_entries(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    organization_id: Optional[str] = Query(None),
    crop_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await init_field_notebook_table(db)
    user_id = str(current_user.id)
    try:
        clauses = ["user_id = :user_id"]
        params: dict[str, Any] = {"user_id": user_id}
        if date_from:
            clauses.append("entry_date >= :date_from")
            params["date_from"] = date_from
        if date_to:
            clauses.append("entry_date <= :date_to")
            params["date_to"] = date_to
        if organization_id:
            clauses.append(
                "(organization_id = :organization_id OR organization_id IS NULL)"
            )
            params["organization_id"] = organization_id
        if crop_id:
            clauses.append("crop_id = :crop_id")
            params["crop_id"] = crop_id

        result = await db.execute(
            text(
                f"""
                SELECT {ENTRY_COLUMNS}
                FROM field_notebook_entries
                WHERE {' AND '.join(clauses)}
                ORDER BY entry_date DESC, created_at DESC
                """
            ),
            params,
        )
        rows = [_serialize(dict(r)) for r in result.mappings().all()]
        return {"count": len(rows), "data": rows}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"No se pudieron cargar las anotaciones: {exc}"
        ) from exc


@router.post("/", status_code=201)
async def create_entry(
    data: NotebookCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await init_field_notebook_table(db)
    entry_id = str(uuid4())
    crop_id = data.crop_id or None
    try:
        await db.execute(
            text(
                """
                INSERT INTO field_notebook_entries (
                    id, user_id, organization_id, crop_id, entry_date,
                    title, body, category, reminder_at
                ) VALUES (
                    :id, :user_id, :organization_id, :crop_id, :entry_date,
                    :title, :body, :category, :reminder_at
                )
                """
            ),
            {
                "id": entry_id,
                "user_id": str(current_user.id),
                "organization_id": data.organization_id,
                "crop_id": crop_id,
                "entry_date": data.entry_date,
                "title": data.title.strip(),
                "body": (data.body or "").strip() or None,
                "category": data.category,
                "reminder_at": data.reminder_at,
            },
        )
        await db.commit()
        created = await db.execute(
            text(
                f"""
                SELECT {ENTRY_COLUMNS}
                FROM field_notebook_entries
                WHERE id = :id
                """
            ),
            {"id": entry_id},
        )
        row = created.mappings().first()
        return {"status": "success", "data": _serialize(dict(row)) if row else {"id": entry_id}}
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"No se pudo guardar la anotación: {exc}"
        ) from exc


@router.patch("/{entry_id}", status_code=200)
async def update_entry(
    entry_id: str,
    data: NotebookUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await init_field_notebook_table(db)
    payload = data.model_dump(exclude_unset=True)
    if "title" in payload and isinstance(payload["title"], str):
        payload["title"] = payload["title"].strip()
    if "body" in payload and isinstance(payload["body"], str):
        payload["body"] = payload["body"].strip() or None
    if not payload:
        raise HTTPException(status_code=400, detail="No hay cambios")

    assignments = [f"{key} = :{key}" for key in payload]
    params = {
        **payload,
        "id": entry_id,
        "user_id": str(current_user.id),
    }
    result = await db.execute(
        text(
            f"""
            UPDATE field_notebook_entries
            SET {', '.join(assignments)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id AND user_id = :user_id
            """
        ),
        params,
    )
    if result.rowcount == 0:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Anotación no encontrada")
    await db.commit()
    refreshed = await db.execute(
        text(
            f"""
            SELECT {ENTRY_COLUMNS}
            FROM field_notebook_entries
            WHERE id = :id
            """
        ),
        {"id": entry_id},
    )
    row = refreshed.mappings().first()
    return {"status": "success", "data": _serialize(dict(row)) if row else {"id": entry_id}}


@router.delete("/{entry_id}", status_code=200)
async def delete_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await init_field_notebook_table(db)
    result = await db.execute(
        text(
            """
            DELETE FROM field_notebook_entries
            WHERE id = :id AND user_id = :user_id
            """
        ),
        {"id": entry_id, "user_id": str(current_user.id)},
    )
    if result.rowcount == 0:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Anotación no encontrada")
    await db.commit()
    return {"status": "success", "id": entry_id}
