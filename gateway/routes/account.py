"""Perfil, tokens de acceso, uso y soporte del usuario autenticado."""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.security import user_is_admin
from models.user import User
from routes.auth import create_access_token, get_current_user
from services.database import get_db
from services.evaluation_dataset import safe_rollback

router = APIRouter(prefix="/account", tags=["Account"])

ENSURE_TABLES = (
    """
    CREATE TABLE IF NOT EXISTS user_access_tokens (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR(100) NOT NULL,
        kind VARCHAR(20) NOT NULL DEFAULT 'access',
        token_prefix VARCHAR(24) NOT NULL,
        token_hash VARCHAR(64) NOT NULL UNIQUE,
        jti UUID NOT NULL UNIQUE,
        expires_at TIMESTAMP WITHOUT TIME ZONE,
        last_used_at TIMESTAMP WITHOUT TIME ZONE,
        revoked_at TIMESTAMP WITHOUT TIME ZONE,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS support_tickets (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
        subject VARCHAR(200) NOT NULL,
        message TEXT NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'open',
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        job_title VARCHAR(80),
        phone VARCHAR(30),
        island VARCHAR(40),
        municipality VARCHAR(80),
        bio TEXT,
        crop_focus VARCHAR(80),
        preferred_language VARCHAR(8) NOT NULL DEFAULT 'es',
        notify_email BOOLEAN NOT NULL DEFAULT TRUE,
        notify_whatsapp BOOLEAN NOT NULL DEFAULT FALSE,
        avatar_path TEXT,
        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )
    """,
)


async def ensure_account_tables(db: AsyncSession) -> None:
    for statement in ENSURE_TABLES:
        await db.execute(text(statement))
    await db.commit()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def resolve_managed_user(
    db: AsyncSession,
    current_user: User,
    user_id: uuid.UUID | None,
    organization_id: uuid.UUID | None = None,
) -> User:
    """Devuelve el usuario objetivo. Un admin puede gestionar n cuentas de su org."""
    if user_id is None or str(user_id) == str(current_user.id):
        return current_user
    if not await user_is_admin(db, current_user.id):
        raise HTTPException(
            status_code=403,
            detail="Solo un administrador puede gestionar otras cuentas",
        )
    params = {
        "admin_id": current_user.id,
        "target_id": user_id,
        "organization_id": organization_id,
    }
    org_clause = "AND a.organization_id = :organization_id" if organization_id else ""
    shared = await db.scalar(
        text(f"""
            SELECT 1
            FROM organization_members a
            JOIN organization_members b
              ON a.organization_id = b.organization_id
            WHERE a.user_id = :admin_id
              AND b.user_id = :target_id
              AND a.active = true
              AND b.active = true
              {org_clause}
            LIMIT 1
            """),
        params,
    )
    if not shared:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    target = await db.scalar(
        select(User).where(User.id == user_id, User.active.is_(True))
    )
    if target is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return target


AVATAR_ROOT = Path(
    os.getenv(
        "AVATAR_STORAGE_ROOT",
        Path(__file__).resolve().parent.parent / "uploads" / "avatars",
    )
)
AVATAR_MAX_BYTES = 2 * 1024 * 1024
AVATAR_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _clean(value: str | None, max_len: int) -> str | None:
    if value is None:
        return None
    text_value = value.strip()
    if not text_value:
        return None
    return text_value[:max_len]


def _profile_defaults() -> dict:
    return {
        "job_title": None,
        "phone": None,
        "island": None,
        "municipality": None,
        "bio": None,
        "crop_focus": None,
        "preferred_language": "es",
        "notify_email": True,
        "notify_whatsapp": False,
        "has_avatar": False,
    }


async def profile_payload(db: AsyncSession, user: User) -> dict:
    await ensure_account_tables(db)
    row = (
        (
            await db.execute(
                text("""
                    SELECT job_title, phone, island, municipality, bio, crop_focus,
                           preferred_language, notify_email, notify_whatsapp,
                           avatar_path, updated_at
                    FROM user_profiles
                    WHERE user_id = :user_id
                    """),
                {"user_id": user.id},
            )
        )
        .mappings()
        .first()
        or {}
    )
    payload = _profile_defaults()
    payload.update(
        {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "job_title": row.get("job_title"),
            "phone": row.get("phone"),
            "island": row.get("island"),
            "municipality": row.get("municipality"),
            "bio": row.get("bio"),
            "crop_focus": row.get("crop_focus"),
            "preferred_language": row.get("preferred_language") or "es",
            "notify_email": bool(
                row["notify_email"] if row.get("notify_email") is not None else True
            ),
            "notify_whatsapp": bool(row.get("notify_whatsapp") or False),
            "has_avatar": bool(row.get("avatar_path")),
        }
    )
    return payload


async def _upsert_profile(db: AsyncSession, user_id, data: dict) -> None:
    def field(name: str, default=None):
        if name not in data:
            return default, False
        value = data[name]
        if isinstance(value, str):
            value = _clean(value, 500 if name == "bio" else 80)
        return value, True

    job_title, set_job = field("job_title")
    phone, set_phone = field("phone", None)
    island, set_island = field("island")
    municipality, set_muni = field("municipality")
    bio, set_bio = field("bio")
    crop_focus, set_crop = field("crop_focus")
    language, set_lang = field("preferred_language", "es")
    notify_email, set_email = field("notify_email", True)
    notify_whatsapp, set_wa = field("notify_whatsapp", False)
    avatar_path, set_avatar = field("avatar_path")
    if language not in {"es", "en"}:
        language = "es"
    await db.execute(
        text("""
            INSERT INTO user_profiles (
                user_id, job_title, phone, island, municipality, bio, crop_focus,
                preferred_language, notify_email, notify_whatsapp, avatar_path, updated_at
            ) VALUES (
                :user_id, :job_title, :phone, :island, :municipality, :bio, :crop_focus,
                COALESCE(:preferred_language, 'es'),
                COALESCE(:notify_email, TRUE),
                COALESCE(:notify_whatsapp, FALSE),
                :avatar_path, NOW()
            )
            ON CONFLICT (user_id) DO UPDATE SET
                job_title = CASE WHEN :set_job THEN :job_title ELSE user_profiles.job_title END,
                phone = CASE WHEN :set_phone THEN :phone ELSE user_profiles.phone END,
                island = CASE WHEN :set_island THEN :island ELSE user_profiles.island END,
                municipality = CASE WHEN :set_muni THEN :municipality ELSE user_profiles.municipality END,
                bio = CASE WHEN :set_bio THEN :bio ELSE user_profiles.bio END,
                crop_focus = CASE WHEN :set_crop THEN :crop_focus ELSE user_profiles.crop_focus END,
                preferred_language = CASE WHEN :set_lang THEN :preferred_language ELSE user_profiles.preferred_language END,
                notify_email = CASE WHEN :set_email THEN :notify_email ELSE user_profiles.notify_email END,
                notify_whatsapp = CASE WHEN :set_wa THEN :notify_whatsapp ELSE user_profiles.notify_whatsapp END,
                avatar_path = CASE WHEN :set_avatar THEN :avatar_path ELSE user_profiles.avatar_path END,
                updated_at = NOW()
            """),
        {
            "user_id": user_id,
            "job_title": job_title,
            "phone": phone,
            "island": island,
            "municipality": municipality,
            "bio": bio,
            "crop_focus": crop_focus,
            "preferred_language": language,
            "notify_email": notify_email,
            "notify_whatsapp": notify_whatsapp,
            "avatar_path": avatar_path,
            "set_job": set_job,
            "set_phone": set_phone,
            "set_island": set_island,
            "set_muni": set_muni,
            "set_bio": set_bio,
            "set_crop": set_crop,
            "set_lang": set_lang,
            "set_email": set_email,
            "set_wa": set_wa,
            "set_avatar": set_avatar,
        },
    )


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    job_title: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, max_length=30)
    island: str | None = Field(default=None, max_length=40)
    municipality: str | None = Field(default=None, max_length=80)
    bio: str | None = Field(default=None, max_length=500)
    crop_focus: str | None = Field(default=None, max_length=80)
    preferred_language: str | None = Field(default=None, max_length=8)
    notify_email: bool | None = None
    notify_whatsapp: bool | None = None


class TokenCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    kind: str = Field(default="access")
    expires_days: int = Field(default=30, ge=1, le=365)


class SupportCreate(BaseModel):
    subject: str = Field(min_length=4, max_length=200)
    message: str = Field(min_length=10, max_length=4000)
    organization_id: str | None = None


@router.get("/users")
async def list_managed_users(
    organization_id: uuid.UUID | None = None,
    q: str = "",
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Directorio paginado de n usuarios de la organización."""
    limit = min(max(limit, 1), 50)
    offset = max(offset, 0)
    is_admin = await user_is_admin(db, current_user.id)
    self_item = {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
        "role": None,
        "active": True,
        "is_self": True,
    }
    if not is_admin:
        return {
            "is_admin": False,
            "total": 1,
            "limit": limit,
            "offset": 0,
            "items": [self_item],
        }
    if organization_id is None:
        raise HTTPException(status_code=400, detail="Selecciona una organización")
    member = await db.scalar(
        text("""
            SELECT 1 FROM organization_members
            WHERE organization_id = :org_id AND user_id = :user_id AND active = true
            """),
        {"org_id": organization_id, "user_id": current_user.id},
    )
    if not member:
        raise HTTPException(status_code=403, detail="No perteneces a esta organización")
    query = q.strip()
    like = f"%{query}%"
    rows = (
        (
            await db.execute(
                text("""
                    SELECT
                        u.id,
                        u.name,
                        u.email,
                        u.active,
                        r.name AS role,
                        COUNT(*) OVER() AS total
                    FROM organization_members om
                    JOIN users u ON u.id = om.user_id
                    LEFT JOIN roles r ON r.id = om.role_id
                    WHERE om.organization_id = :org_id
                      AND om.active = true
                      AND (
                          :query = ''
                          OR u.name ILIKE :like
                          OR u.email ILIKE :like
                      )
                    ORDER BY u.name ASC
                    LIMIT :limit OFFSET :offset
                    """),
                {
                    "org_id": organization_id,
                    "query": query,
                    "like": like,
                    "limit": limit,
                    "offset": offset,
                },
            )
        )
        .mappings()
        .all()
    )
    total = int(rows[0]["total"]) if rows else 0
    return {
        "is_admin": True,
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "email": row["email"],
                "role": row["role"],
                "active": bool(row["active"]),
                "is_self": str(row["id"]) == str(current_user.id),
            }
            for row in rows
        ],
    }


@router.get("/profile")
async def get_profile(
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await resolve_managed_user(db, current_user, user_id, organization_id)
    return await profile_payload(db, target)


@router.patch("/profile")
async def update_profile(
    payload: ProfileUpdate,
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await resolve_managed_user(db, current_user, user_id, organization_id)
    data = payload.model_dump(exclude_unset=True)
    name = data.get("name")
    if name is not None:
        name = name.strip()
        if len(name) < 2:
            raise HTTPException(status_code=400, detail="El nombre es demasiado corto")
        await db.execute(
            text("UPDATE users SET name = :name WHERE id = :id"),
            {"name": name, "id": target.id},
        )
        target.name = name
    profile_data = {key: value for key, value in data.items() if key != "name"}
    if profile_data:
        await _upsert_profile(db, target.id, profile_data)
    await db.commit()
    refreshed = await db.scalar(select(User).where(User.id == target.id))
    return await profile_payload(db, refreshed or target)


@router.post("/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await resolve_managed_user(db, current_user, user_id, organization_id)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Imagen vacía")
    if len(content) > AVATAR_MAX_BYTES:
        raise HTTPException(status_code=400, detail="La imagen no puede superar 2 MB")
    suffix = AVATAR_TYPES.get((file.content_type or "").lower())
    if suffix is None:
        raise HTTPException(status_code=400, detail="Usa JPG, PNG o WEBP")
    AVATAR_ROOT.mkdir(parents=True, exist_ok=True)
    path = AVATAR_ROOT / f"{target.id}{suffix}"
    for old in AVATAR_ROOT.glob(f"{target.id}.*"):
        if old != path:
            old.unlink(missing_ok=True)
    path.write_bytes(content)
    await _upsert_profile(db, target.id, {"avatar_path": str(path)})
    await db.commit()
    return await profile_payload(db, target)


@router.get("/profile/avatar")
async def get_avatar(
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await resolve_managed_user(db, current_user, user_id, organization_id)
    await ensure_account_tables(db)
    stored = await db.scalar(
        text("SELECT avatar_path FROM user_profiles WHERE user_id = :user_id"),
        {"user_id": target.id},
    )
    if not stored or not Path(str(stored)).exists():
        raise HTTPException(status_code=404, detail="Sin foto de perfil")
    return FileResponse(str(stored))


@router.delete("/profile/avatar")
async def delete_avatar(
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await resolve_managed_user(db, current_user, user_id, organization_id)
    await ensure_account_tables(db)
    stored = await db.scalar(
        text("SELECT avatar_path FROM user_profiles WHERE user_id = :user_id"),
        {"user_id": target.id},
    )
    if stored:
        Path(str(stored)).unlink(missing_ok=True)
    await db.execute(
        text("""
            UPDATE user_profiles
            SET avatar_path = NULL, updated_at = NOW()
            WHERE user_id = :user_id
            """),
        {"user_id": target.id},
    )
    await db.commit()
    return await profile_payload(db, target)


@router.get("/tokens")
async def list_tokens(
    kind: str | None = None,
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await resolve_managed_user(db, current_user, user_id, organization_id)
    await ensure_account_tables(db)
    clause = "AND kind = :kind" if kind else ""
    params = {"user_id": target.id}
    if kind:
        params["kind"] = kind
    rows = (
        (
            await db.execute(
                text(f"""
                    SELECT id, name, kind, token_prefix, expires_at, last_used_at,
                           revoked_at, created_at
                    FROM user_access_tokens
                    WHERE user_id = :user_id {clause}
                    ORDER BY created_at DESC
                    """),
                params,
            )
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]


@router.post("/tokens")
async def create_token(
    payload: TokenCreate,
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await resolve_managed_user(db, current_user, user_id, organization_id)
    await ensure_account_tables(db)
    kind = payload.kind if payload.kind in {"access", "api_key"} else "access"
    jti = uuid.uuid4()
    expires_minutes = payload.expires_days * 24 * 60
    token = create_access_token(
        target.id,
        target.email,
        expires_minutes=expires_minutes,
        jti=str(jti),
        token_use=kind,
    )
    prefix = f"agro_{str(jti).replace('-', '')[:8]}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_days)
    token_id = uuid.uuid4()
    await db.execute(
        text("""
            INSERT INTO user_access_tokens (
                id, user_id, name, kind, token_prefix, token_hash, jti, expires_at
            ) VALUES (
                :id, :user_id, :name, :kind, :prefix, :token_hash, :jti, :expires_at
            )
            """),
        {
            "id": token_id,
            "user_id": target.id,
            "name": payload.name.strip(),
            "kind": kind,
            "prefix": prefix,
            "token_hash": _hash_token(token),
            "jti": str(jti),
            "expires_at": expires_at.replace(tzinfo=None),
        },
    )
    await db.commit()
    return {
        "id": str(token_id),
        "name": payload.name.strip(),
        "kind": kind,
        "prefix": prefix,
        "expires_at": expires_at.isoformat(),
        "token": token,
        "token_type": "Bearer",
        "user_id": str(target.id),
        "note": "Copia el token ahora. No se volverá a mostrar.",
    }


@router.delete("/tokens/{token_id}")
async def revoke_token(
    token_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await resolve_managed_user(db, current_user, user_id, organization_id)
    await ensure_account_tables(db)
    updated = await db.scalar(
        text("""
            UPDATE user_access_tokens
            SET revoked_at = NOW()
            WHERE id = :id AND user_id = :user_id AND revoked_at IS NULL
            RETURNING id
            """),
        {"id": token_id, "user_id": target.id},
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Token no encontrado")
    await db.commit()
    return {"status": "revoked", "id": str(token_id)}


@router.get("/usage")
async def account_usage(
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await resolve_managed_user(db, current_user, user_id, organization_id)

    async def _count(sql: str) -> int:
        try:
            value = await db.scalar(text(sql), {"user_id": target.id})
            return int(value or 0)
        except Exception:
            await safe_rollback(db)
            return 0

    documents = await _count("SELECT COUNT(*) FROM documents WHERE owner_id = :user_id")
    conversations = await _count(
        "SELECT COUNT(*) FROM conversations WHERE user_id = :user_id"
    )
    api_calls = await _count("SELECT COUNT(*) FROM api_logs WHERE user_id = :user_id")
    tokens = 0
    try:
        await ensure_account_tables(db)
        tokens = int(
            await db.scalar(
                text("""
                    SELECT COUNT(*) FROM user_access_tokens
                    WHERE user_id = :user_id AND revoked_at IS NULL
                    """),
                {"user_id": target.id},
            )
            or 0
        )
    except Exception:
        await safe_rollback(db)
    return {
        "user_id": str(target.id),
        "documents": documents,
        "conversations": conversations,
        "api_calls": api_calls,
        "active_tokens": tokens,
    }


@router.get("/projects")
async def account_projects(
    organization_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await resolve_managed_user(db, current_user, user_id, organization_id)
    member = await db.scalar(
        text("""
            SELECT 1 FROM organization_members
            WHERE organization_id = :org_id AND user_id = :user_id AND active = true
            """),
        {"org_id": organization_id, "user_id": current_user.id},
    )
    if not member:
        raise HTTPException(status_code=403, detail="No perteneces a esta organización")
    rows = (
        (
            await db.execute(
                text("""
                    SELECT
                        kb.id,
                        kb.name,
                        kb.description,
                        kb.created_by,
                        kb.created_at,
                        (
                            SELECT COUNT(*) FROM documents d
                            WHERE d.knowledge_base_id = kb.id
                              AND d.owner_id = :user_id
                        ) AS document_count
                    FROM knowledge_bases kb
                    JOIN tenants t ON t.id = kb.tenant_id
                    WHERE t.organization_id = :org_id
                      AND t.active = true
                    ORDER BY kb.name
                    """),
                {"org_id": organization_id, "user_id": target.id},
            )
        )
        .mappings()
        .all()
    )
    return {
        "user_id": str(target.id),
        "items": [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "description": row["description"],
                "created_by": (str(row["created_by"]) if row["created_by"] else None),
                "created_at": row["created_at"],
                "document_count": int(row["document_count"] or 0),
                "owned": str(row["created_by"] or "") == str(target.id),
            }
            for row in rows
        ],
    }


@router.get("/admins")
async def list_org_admins(
    organization_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    params: dict = {"user_id": current_user.id}
    org_filter = ""
    if organization_id:
        params["organization_id"] = organization_id
        org_filter = "AND o.id = :organization_id"
    rows = (
        (
            await db.execute(
                text(f"""
                    SELECT DISTINCT u.id, u.name, o.name AS organization_name
                    FROM organization_members om
                    JOIN users u ON u.id = om.user_id
                    JOIN organizations o ON o.id = om.organization_id
                    JOIN roles r ON r.id = om.role_id
                    WHERE om.active = true
                      AND lower(r.name) IN ('admin', 'super_admin', 'org_admin')
                      AND om.organization_id IN (
                          SELECT organization_id FROM organization_members
                          WHERE user_id = :user_id AND active = true
                      )
                      {org_filter}
                    ORDER BY u.name
                    """),
                params,
            )
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]


@router.get("/support")
async def list_support_tickets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_account_tables(db)
    is_admin = await user_is_admin(db, current_user.id)
    if is_admin:
        rows = (await db.execute(text("""
                        SELECT t.id, t.subject, t.message, t.status, t.created_at,
                               u.name AS author_name, u.email AS author_email,
                               o.name AS organization_name
                        FROM support_tickets t
                        JOIN users u ON u.id = t.user_id
                        LEFT JOIN organizations o ON o.id = t.organization_id
                        ORDER BY t.created_at DESC
                        LIMIT 100
                        """))).mappings().all()
    else:
        rows = (
            (
                await db.execute(
                    text("""
                        SELECT t.id, t.subject, t.message, t.status, t.created_at,
                               u.name AS author_name, u.email AS author_email,
                               o.name AS organization_name
                        FROM support_tickets t
                        JOIN users u ON u.id = t.user_id
                        LEFT JOIN organizations o ON o.id = t.organization_id
                        WHERE t.user_id = :user_id
                        ORDER BY t.created_at DESC
                        """),
                    {"user_id": current_user.id},
                )
            )
            .mappings()
            .all()
        )
    return {"is_admin": is_admin, "tickets": [dict(row) for row in rows]}


@router.post("/support")
async def create_support_ticket(
    payload: SupportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_account_tables(db)
    ticket_id = uuid.uuid4()
    await db.execute(
        text("""
            INSERT INTO support_tickets (id, user_id, organization_id, subject, message)
            VALUES (:id, :user_id, :organization_id, :subject, :message)
            """),
        {
            "id": ticket_id,
            "user_id": current_user.id,
            "organization_id": payload.organization_id,
            "subject": payload.subject.strip(),
            "message": payload.message.strip(),
        },
    )
    await db.commit()
    return {"id": str(ticket_id), "status": "open"}
