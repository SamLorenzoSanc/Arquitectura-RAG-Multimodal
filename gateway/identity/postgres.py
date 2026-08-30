from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from core.exceptions import AppError
from utils.scope import ensure_agrotech_membership

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


class PostgresIdentityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_orm_by_id(self, user_id):
        return await self.db.scalar(
            select(User).where(User.id == user_id, User.active.is_(True))
        )

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        row = (
            (
                await self.db.execute(
                    text("SELECT * FROM users WHERE email = :email"),
                    {"email": email},
                )
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    async def email_exists(self, email: str) -> bool:
        return bool(
            await self.db.scalar(
                text("SELECT id FROM users WHERE email = :email"), {"email": email}
            )
        )

    async def register(self, name: str, email: str, password_hash: str):
        org_id = str(uuid.uuid4())
        await self.db.execute(
            text("""
                INSERT INTO organizations (id, name, description, active)
                VALUES (:id, :name, :description, :active)
            """),
            {
                "id": org_id,
                "name": f"{name} Organization",
                "description": "Organización por defecto para nuevos usuarios",
                "active": True,
            },
        )
        new_user_id = await self.db.scalar(
            text("""
                INSERT INTO users (name, email, password_hash)
                VALUES (:name, :email, :password) RETURNING id
            """),
            {"name": name, "email": email, "password": password_hash},
        )
        role_id = await self.db.scalar(
            text("""
                SELECT id FROM roles
                WHERE name = 'ORG_ADMIN' AND organization_id IS NULL
                LIMIT 1
            """)
        )
        if not role_id:
            raise AppError(
                "Error crítico: No existe el rol ORG_ADMIN global en el sistema.",
                500,
            )
        await self.db.execute(
            text("""
                INSERT INTO organization_members (organization_id, user_id, role_id, active)
                VALUES (:org_id, :user_id, :role_id, true)
            """),
            {"org_id": org_id, "user_id": new_user_id, "role_id": role_id},
        )
        tenant_id = str(uuid.uuid4())
        await self.db.execute(
            text("""
                INSERT INTO tenants (id, organization_id, name, description, active)
                VALUES (:id, :organization_id, :name, :description, true)
            """),
            {
                "id": tenant_id,
                "organization_id": org_id,
                "name": "Default",
                "description": "Tenant principal",
            },
        )
        knowledge_base_id = str(uuid.uuid4())
        await self.db.execute(
            text("""
                INSERT INTO knowledge_bases (id, tenant_id, name, description, chroma_collection)
                VALUES (:id, :tenant_id, :name, :description, :chroma_collection)
            """),
            {
                "id": knowledge_base_id,
                "tenant_id": tenant_id,
                "name": "General",
                "description": "Knowledge Base por defecto",
                "chroma_collection": f"col_{tenant_id.replace('-', '')}",
            },
        )
        await self.ensure_agrotech(new_user_id)
        await self.db.commit()
        return new_user_id

    async def list_users(self) -> list[dict[str, Any]]:
        rows = (
            await self.db.execute(
                text("""
            SELECT id, name, email, active, created_at
            FROM users
            """)
            )
        ).mappings().all()
        return [dict(r) for r in rows]

    async def list_roles(self) -> list[dict[str, Any]]:
        rows = (
            await self.db.execute(
                text("SELECT id, name, description, organization_id FROM roles")
            )
        ).mappings().all()
        return [dict(r) for r in rows]

    async def list_user_roles(self, user_id) -> list[dict[str, Any]]:
        rows = (
            await self.db.execute(
                text("""
            SELECT
                o.id AS organization_id,
                o.name AS organization_name,
                r.name AS role_name,
                r.description AS role_description
            FROM organization_members om
            JOIN organizations o ON o.id = om.organization_id
            LEFT JOIN roles r ON r.id = om.role_id
            WHERE om.user_id = :user_id AND om.active = true
        """),
                {"user_id": user_id},
            )
        ).mappings().all()
        return [dict(r) for r in rows]

    async def is_admin(self, user_id) -> bool:
        return bool(
            await self.db.scalar(
                text("""
                SELECT EXISTS (
                    SELECT 1
                    FROM organization_members AS membership
                    JOIN roles AS role ON role.id = membership.role_id
                    WHERE membership.user_id = :user_id
                      AND membership.active = true
                      AND lower(role.name) IN (
                          'admin', 'super_admin', 'org_admin'
                      )
                )
                """),
                {"user_id": user_id},
            )
        )

    async def ensure_agrotech(self, user_id) -> None:
        await ensure_agrotech_membership(self.db, user_id)

    async def revoke_session(self, token: str, expires_at) -> None:
        await self.db.execute(
            text("""
            CREATE TABLE IF NOT EXISTS revoked_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                token TEXT NOT NULL,
                expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                revoked_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
            """)
        )
        await self.db.execute(
            text(
                "INSERT INTO revoked_tokens (token, expires_at) VALUES (:token, :expires)"
            ),
            {"token": token, "expires": expires_at},
        )
        await self.db.commit()

    async def assert_access_token_active(self, jti: str, user_id) -> None:
        try:
            row = (
                (
                    await self.db.execute(
                        text("""
                            SELECT revoked_at FROM user_access_tokens
                            WHERE jti = :jti AND user_id = :user_id
                            """),
                        {"jti": jti, "user_id": user_id},
                    )
                )
                .mappings()
                .first()
            )
        except Exception as exc:
            await self.db.rollback()
            raise AppError("Token revocado o inválido", 401) from exc
        if row is None or row.get("revoked_at") is not None:
            raise AppError("Token revocado o inválido", 401)
        await self.db.execute(
            text("""
                UPDATE user_access_tokens
                SET last_used_at = NOW()
                WHERE jti = :jti AND user_id = :user_id
                """),
            {"jti": jti, "user_id": user_id},
        )

    async def ensure_tables(self) -> None:
        for statement in ENSURE_TABLES:
            await self.db.execute(text(statement))
        await self.db.commit()

    async def resolve_managed_user(
        self, current_user, user_id, organization_id=None
    ):
        if user_id is None or str(user_id) == str(current_user.id):
            return current_user
        if not await self.is_admin(current_user.id):
            raise AppError("Solo un administrador puede gestionar otras cuentas", 403)
        params = {
            "admin_id": current_user.id,
            "target_id": user_id,
            "organization_id": organization_id,
        }
        org_clause = "AND a.organization_id = :organization_id" if organization_id else ""
        shared = await self.db.scalar(
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
            raise AppError("Usuario no encontrado", 404)
        target = await self.db.scalar(
            select(User).where(User.id == user_id, User.active.is_(True))
        )
        if target is None:
            raise AppError("Usuario no encontrado", 404)
        return target

    async def profile_payload(self, user) -> dict[str, Any]:
        await self.ensure_tables()
        row = (
            (
                await self.db.execute(
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
        return {
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

    async def update_name(self, user_id, name: str) -> None:
        await self.db.execute(
            text("UPDATE users SET name = :name WHERE id = :id"),
            {"name": name, "id": user_id},
        )

    async def upsert_profile(self, user_id, data: dict[str, Any]) -> None:
        def field(name: str, default=None):
            if name not in data:
                return default, False
            value = data[name]
            if isinstance(value, str):
                text_value = value.strip()
                value = (text_value[:500] if name == "bio" else text_value[:80]) or None
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
        await self.db.execute(
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

    async def get_avatar_path(self, user_id) -> str | None:
        await self.ensure_tables()
        return await self.db.scalar(
            text("SELECT avatar_path FROM user_profiles WHERE user_id = :user_id"),
            {"user_id": user_id},
        )

    async def clear_avatar(self, user_id) -> None:
        await self.db.execute(
            text("""
            UPDATE user_profiles
            SET avatar_path = NULL, updated_at = NOW()
            WHERE user_id = :user_id
            """),
            {"user_id": user_id},
        )

    async def list_tokens(self, user_id, kind: str | None = None) -> list[dict]:
        await self.ensure_tables()
        clause = "AND kind = :kind" if kind else ""
        params = {"user_id": user_id}
        if kind:
            params["kind"] = kind
        rows = (
            (
                await self.db.execute(
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

    async def insert_token(self, row: dict[str, Any]) -> None:
        await self.ensure_tables()
        await self.db.execute(
            text("""
            INSERT INTO user_access_tokens (
                id, user_id, name, kind, token_prefix, token_hash, jti, expires_at
            ) VALUES (
                :id, :user_id, :name, :kind, :prefix, :token_hash, :jti, :expires_at
            )
            """),
            row,
        )
        await self.db.commit()

    async def revoke_token(self, token_id, user_id):
        await self.ensure_tables()
        updated = await self.db.scalar(
            text("""
            UPDATE user_access_tokens
            SET revoked_at = NOW()
            WHERE id = :id AND user_id = :user_id AND revoked_at IS NULL
            RETURNING id
            """),
            {"id": token_id, "user_id": user_id},
        )
        if updated is None:
            raise AppError("Token no encontrado", 404)
        await self.db.commit()
        return updated

    async def usage(self, user_id) -> dict[str, int]:
        from evaluation.dataset_schema import safe_rollback

        async def _count(sql: str) -> int:
            try:
                value = await self.db.scalar(text(sql), {"user_id": user_id})
                return int(value or 0)
            except Exception:
                await safe_rollback(self.db)
                return 0

        documents = await _count(
            "SELECT COUNT(*) FROM documents WHERE owner_id = :user_id"
        )
        conversations = await _count(
            "SELECT COUNT(*) FROM conversations WHERE user_id = :user_id"
        )
        api_calls = await _count(
            "SELECT COUNT(*) FROM api_logs WHERE user_id = :user_id"
        )
        tokens = 0
        try:
            await self.ensure_tables()
            tokens = int(
                await self.db.scalar(
                    text("""
                    SELECT COUNT(*) FROM user_access_tokens
                    WHERE user_id = :user_id AND revoked_at IS NULL
                    """),
                    {"user_id": user_id},
                )
                or 0
            )
        except Exception:
            await safe_rollback(self.db)
        return {
            "documents": documents,
            "conversations": conversations,
            "api_calls": api_calls,
            "active_tokens": tokens,
        }

    async def analytics(self, user_id) -> dict[str, Any]:
        from evaluation.dataset_schema import safe_rollback

        empty = {
            "totals": {
                "documents": 0,
                "conversations": 0,
                "questions": 0,
                "projects": 0,
                "organizations": 0,
                "api_calls": 0,
                "active_tokens": 0,
                "support_tickets": 0,
                "documents_week": 0,
                "questions_week": 0,
            },
            "activity": [],
            "recent_documents": [],
            "recent_conversations": [],
            "projects": [],
            "timeline": [],
        }
        params = {"user_id": str(user_id)}

        async def _count(sql: str) -> int:
            try:
                value = await self.db.scalar(text(sql), params)
                return int(value or 0)
            except Exception:
                await safe_rollback(self.db)
                return 0

        async def _rows(sql: str) -> list[dict]:
            try:
                result = await self.db.execute(text(sql), params)
                return [dict(row) for row in result.mappings().all()]
            except Exception:
                await safe_rollback(self.db)
                return []

        def _iso(value):
            if value is None:
                return None
            if hasattr(value, "isoformat"):
                return value.isoformat()
            return str(value)

        try:
            await self.ensure_tables()
            await self.db.execute(
                text(
                    "ALTER TABLE knowledge_bases ADD COLUMN IF NOT EXISTS use_case VARCHAR(80)"
                )
            )
        except Exception:
            await safe_rollback(self.db)

        documents = await _count(
            "SELECT COUNT(*) FROM documents WHERE owner_id = CAST(:user_id AS uuid)"
        )
        conversations = await _count(
            "SELECT COUNT(*) FROM conversations WHERE user_id = CAST(:user_id AS uuid)"
        )
        questions = await _count(
            """
            SELECT COUNT(*) FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.user_id = CAST(:user_id AS uuid) AND m.role = 'user'
            """
        )
        projects = await _count(
            "SELECT COUNT(*) FROM knowledge_bases WHERE created_by = CAST(:user_id AS uuid)"
        )
        organizations = await _count(
            """
            SELECT COUNT(*) FROM organization_members
            WHERE user_id = CAST(:user_id AS uuid) AND active = true
            """
        )
        api_calls = await _count(
            """
            SELECT CASE
                WHEN to_regclass('public.api_logs') IS NULL THEN 0
                ELSE (
                    SELECT COUNT(*) FROM api_logs
                    WHERE user_id = CAST(:user_id AS uuid)
                )
            END
            """
        )
        tickets = await _count(
            """
            SELECT COUNT(*) FROM support_tickets
            WHERE user_id = CAST(:user_id AS uuid)
            """
        )
        tokens = await _count(
            """
            SELECT COUNT(*) FROM user_access_tokens
            WHERE user_id = CAST(:user_id AS uuid) AND revoked_at IS NULL
            """
        )
        documents_week = await _count(
            """
            SELECT COUNT(*) FROM documents
            WHERE owner_id = CAST(:user_id AS uuid)
              AND uploaded_at >= (CURRENT_TIMESTAMP - INTERVAL '7 days')
            """
        )
        questions_week = await _count(
            """
            SELECT COUNT(*) FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.user_id = CAST(:user_id AS uuid)
              AND m.role = 'user'
              AND m.created_at >= (CURRENT_TIMESTAMP - INTERVAL '7 days')
            """
        )

        activity = await _rows(
            """
            SELECT
                g.day::date AS day,
                (
                    SELECT COUNT(*) FROM documents doc
                    WHERE doc.owner_id = CAST(:user_id AS uuid)
                      AND doc.uploaded_at::date = g.day::date
                ) AS documents,
                (
                    SELECT COUNT(*) FROM messages m
                    JOIN conversations c ON c.id = m.conversation_id
                    WHERE c.user_id = CAST(:user_id AS uuid)
                      AND m.role = 'user'
                      AND m.created_at::date = g.day::date
                ) AS questions
            FROM generate_series(
                CURRENT_DATE - 13,
                CURRENT_DATE,
                interval '1 day'
            ) AS g(day)
            ORDER BY day
            """
        )
        recent_documents = await _rows(
            """
            SELECT d.id, d.filename, d.title, d.uploaded_at, kb.name AS project_name
            FROM documents d
            LEFT JOIN knowledge_bases kb ON kb.id = d.knowledge_base_id
            WHERE d.owner_id = CAST(:user_id AS uuid)
            ORDER BY d.uploaded_at DESC NULLS LAST
            LIMIT 6
            """
        )
        recent_conversations = await _rows(
            """
            SELECT
                c.id,
                COALESCE(NULLIF(c.title, ''), 'Conversación') AS title,
                c.updated_at,
                c.created_at,
                (
                    SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id
                ) AS message_count
            FROM conversations c
            WHERE c.user_id = CAST(:user_id AS uuid)
            ORDER BY COALESCE(c.updated_at, c.created_at) DESC
            LIMIT 6
            """
        )
        project_rows = await _rows(
            """
            SELECT
                kb.id,
                kb.name,
                kb.use_case,
                kb.created_at,
                (
                    SELECT COUNT(*) FROM documents d
                    WHERE d.knowledge_base_id = kb.id
                ) AS document_count
            FROM knowledge_bases kb
            WHERE kb.created_by = CAST(:user_id AS uuid)
            ORDER BY kb.created_at DESC
            LIMIT 8
            """
        )
        timeline = await _rows(
            """
            SELECT kind, title, created_at, ref_id FROM (
                SELECT
                    'document'::text AS kind,
                    COALESCE(d.title, d.filename) AS title,
                    d.uploaded_at::timestamptz AS created_at,
                    d.id::text AS ref_id
                FROM documents d
                WHERE d.owner_id = CAST(:user_id AS uuid)
                UNION ALL
                SELECT
                    'conversation',
                    COALESCE(NULLIF(c.title, ''), 'Conversación'),
                    COALESCE(c.updated_at, c.created_at)::timestamptz,
                    c.id::text
                FROM conversations c
                WHERE c.user_id = CAST(:user_id AS uuid)
                UNION ALL
                SELECT
                    'project',
                    kb.name,
                    kb.created_at::timestamptz,
                    kb.id::text
                FROM knowledge_bases kb
                WHERE kb.created_by = CAST(:user_id AS uuid)
            ) events
            ORDER BY created_at DESC NULLS LAST
            LIMIT 12
            """
        )

        try:
            return {
                "totals": {
                    "documents": documents,
                    "conversations": conversations,
                    "questions": questions,
                    "projects": projects,
                    "organizations": organizations,
                    "api_calls": api_calls,
                    "active_tokens": tokens,
                    "support_tickets": tickets,
                    "documents_week": documents_week,
                    "questions_week": questions_week,
                },
                "activity": [
                    {
                        "day": _iso(row.get("day")),
                        "documents": int(row.get("documents") or 0),
                        "questions": int(row.get("questions") or 0),
                    }
                    for row in activity
                ],
                "recent_documents": [
                    {
                        "id": str(row["id"]),
                        "filename": row.get("filename")
                        or row.get("title")
                        or "Documento",
                        "project_name": row.get("project_name"),
                        "uploaded_at": _iso(row.get("uploaded_at")),
                    }
                    for row in recent_documents
                ],
                "recent_conversations": [
                    {
                        "id": str(row["id"]),
                        "title": row.get("title") or "Conversación",
                        "message_count": int(row.get("message_count") or 0),
                        "updated_at": _iso(
                            row.get("updated_at") or row.get("created_at")
                        ),
                    }
                    for row in recent_conversations
                ],
                "projects": [
                    {
                        "id": str(row["id"]),
                        "name": row.get("name") or "Proyecto",
                        "use_case": row.get("use_case") or "Q/A",
                        "document_count": int(row.get("document_count") or 0),
                        "created_at": _iso(row.get("created_at")),
                    }
                    for row in project_rows
                ],
                "timeline": [
                    {
                        "kind": row.get("kind"),
                        "title": row.get("title") or "Actividad",
                        "created_at": _iso(row.get("created_at")),
                        "ref_id": str(row.get("ref_id")) if row.get("ref_id") else None,
                    }
                    for row in timeline
                ],
            }
        except Exception:
            await safe_rollback(self.db)
            return empty

    async def is_org_member(self, organization_id, user_id) -> bool:
        return bool(
            await self.db.scalar(
                text("""
            SELECT 1 FROM organization_members
            WHERE organization_id = :org_id AND user_id = :user_id AND active = true
            """),
                {"org_id": organization_id, "user_id": user_id},
            )
        )

    async def projects(self, organization_id, user_id) -> list[dict]:
        await self.db.execute(
            text(
                "ALTER TABLE knowledge_bases ADD COLUMN IF NOT EXISTS use_case VARCHAR(80)"
            )
        )
        rows = (
            (
                await self.db.execute(
                    text("""
                    SELECT
                        kb.id,
                        kb.name,
                        kb.description,
                        kb.use_case,
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
                    {"org_id": organization_id, "user_id": user_id},
                )
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    async def list_admins(self, user_id, organization_id: str | None) -> list[dict]:
        params: dict = {"user_id": user_id}
        org_filter = ""
        if organization_id:
            params["organization_id"] = organization_id
            org_filter = "AND o.id = :organization_id"
        rows = (
            (
                await self.db.execute(
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

    async def list_support(self, user_id, is_admin: bool) -> list[dict]:
        await self.ensure_tables()
        if is_admin:
            rows = (
                await self.db.execute(
                    text("""
                        SELECT t.id, t.subject, t.message, t.status, t.created_at,
                               u.name AS author_name, u.email AS author_email,
                               o.name AS organization_name
                        FROM support_tickets t
                        JOIN users u ON u.id = t.user_id
                        LEFT JOIN organizations o ON o.id = t.organization_id
                        ORDER BY t.created_at DESC
                        LIMIT 100
                        """)
                )
            ).mappings().all()
        else:
            rows = (
                (
                    await self.db.execute(
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
                        {"user_id": user_id},
                    )
                )
                .mappings()
                .all()
            )
        return [dict(row) for row in rows]

    async def create_support(self, row: dict[str, Any]) -> None:
        await self.ensure_tables()
        await self.db.execute(
            text("""
            INSERT INTO support_tickets (id, user_id, organization_id, subject, message)
            VALUES (:id, :user_id, :organization_id, :subject, :message)
            """),
            row,
        )
        await self.db.commit()

    async def list_managed_users(
        self, organization_id, query: str, limit: int, offset: int
    ) -> list[dict]:
        like = f"%{query}%"
        rows = (
            (
                await self.db.execute(
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
        return [dict(row) for row in rows]

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()
