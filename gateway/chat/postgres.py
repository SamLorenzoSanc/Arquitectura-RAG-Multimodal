from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from core.exceptions import AppError


class PostgresConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(self, user_id) -> list[dict]:
        rows = (
            (
                await self.db.execute(
                    text("""
            SELECT id, title, created_at, updated_at
            FROM conversations
            WHERE user_id = :user_id
            ORDER BY updated_at DESC
            """),
                    {"user_id": user_id},
                )
            )
            .mappings()
            .all()
        )
        return [
            {
                "id": str(conv["id"]),
                "title": conv["title"],
                "created_at": conv["created_at"],
                "updated_at": conv["updated_at"],
            }
            for conv in rows
        ]

    async def list_user_history_for_tenant(
        self,
        tenant_id,
        *,
        user_id_filter: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        """Historial de conversaciones del tenant (memoria a largo plazo del chat)."""
        params: dict = {"tenant_id": tenant_id, "limit": max(1, min(limit, 500))}
        user_clause = ""
        if user_id_filter:
            user_clause = "AND c.user_id = CAST(:user_id AS uuid)"
            params["user_id"] = user_id_filter
        rows = (
            (
                await self.db.execute(
                    text(
                        f"""
            SELECT
                c.id,
                c.title,
                c.created_at,
                c.updated_at,
                c.user_id,
                COALESCE(u.name, u.email, 'Usuario') AS user_name,
                COALESCE(u.email, '') AS user_email,
                (
                    SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id
                ) AS message_count,
                (
                    SELECT LEFT(m.content, 160)
                    FROM messages m
                    WHERE m.conversation_id = c.id AND m.role = 'user'
                    ORDER BY m.created_at ASC
                    LIMIT 1
                ) AS first_user_message
            FROM conversations c
            LEFT JOIN users u ON u.id = c.user_id
            WHERE c.tenant_id = CAST(:tenant_id AS uuid)
              {user_clause}
            ORDER BY COALESCE(c.updated_at, c.created_at) DESC
            LIMIT :limit
            """
                    ),
                    params,
                )
            )
            .mappings()
            .all()
        )
        return [
            {
                "id": str(row["id"]),
                "title": row["title"] or "Conversación",
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "user_id": str(row["user_id"]) if row.get("user_id") else None,
                "user_name": row.get("user_name") or "Usuario",
                "user_email": row.get("user_email") or "",
                "message_count": int(row.get("message_count") or 0),
                "first_user_message": row.get("first_user_message") or "",
            }
            for row in rows
        ]

    async def get_with_messages(self, conversation_id: str, user_id) -> dict:
        conversation = (
            (
                await self.db.execute(
                    text("""
            SELECT id, title, created_at, updated_at
            FROM conversations
            WHERE id = :id AND user_id = :user_id
            """),
                    {"id": conversation_id, "user_id": user_id},
                )
            )
            .mappings()
            .first()
        )
        if not conversation:
            raise AppError("Conversación no encontrada", 404)
        messages = (
            (
                await self.db.execute(
                    text("""
            SELECT id, role, content, created_at
            FROM messages
            WHERE conversation_id = :conversation_id
            ORDER BY created_at ASC
            """),
                    {"conversation_id": conversation_id},
                )
            )
            .mappings()
            .all()
        )
        return {
            "conversation_id": str(conversation["id"]),
            "title": conversation["title"],
            "messages": [
                {"id": str(msg["id"]), "role": msg["role"], "content": msg["content"]}
                for msg in messages
            ],
        }

    async def get_with_messages_for_tenant(
        self, conversation_id: str, tenant_id
    ) -> dict:
        conversation = (
            (
                await self.db.execute(
                    text("""
            SELECT
                c.id,
                c.title,
                c.created_at,
                c.updated_at,
                c.user_id,
                COALESCE(u.name, u.email, 'Usuario') AS user_name,
                COALESCE(u.email, '') AS user_email
            FROM conversations c
            LEFT JOIN users u ON u.id = c.user_id
            WHERE c.id = :id AND c.tenant_id = CAST(:tenant_id AS uuid)
            """),
                    {"id": conversation_id, "tenant_id": tenant_id},
                )
            )
            .mappings()
            .first()
        )
        if not conversation:
            raise AppError("Conversación no encontrada", 404)
        messages = (
            (
                await self.db.execute(
                    text("""
            SELECT id, role, content, created_at
            FROM messages
            WHERE conversation_id = :conversation_id
            ORDER BY created_at ASC
            """),
                    {"conversation_id": conversation_id},
                )
            )
            .mappings()
            .all()
        )
        return {
            "conversation_id": str(conversation["id"]),
            "title": conversation["title"] or "Conversación",
            "user_id": (
                str(conversation["user_id"]) if conversation.get("user_id") else None
            ),
            "user_name": conversation.get("user_name") or "Usuario",
            "user_email": conversation.get("user_email") or "",
            "created_at": conversation.get("created_at"),
            "updated_at": conversation.get("updated_at"),
            "messages": [
                {
                    "id": str(msg["id"]),
                    "role": msg["role"],
                    "content": msg["content"],
                    "created_at": msg.get("created_at"),
                }
                for msg in messages
            ],
        }

    async def delete(self, conversation_id: str, user_id) -> dict:
        conversation = (
            (
                await self.db.execute(
                    text(
                        "SELECT id FROM conversations WHERE id = :id AND user_id = :user_id"
                    ),
                    {"id": conversation_id, "user_id": user_id},
                )
            )
            .mappings()
            .first()
        )
        if not conversation:
            raise AppError("Conversación no encontrada o sin permisos", 404)
        try:
            await self.db.execute(
                text("""
            DELETE FROM message_sources
            WHERE message_id IN (SELECT id FROM messages WHERE conversation_id = :id)
            """),
                {"id": conversation_id},
            )
            await self.db.execute(
                text("DELETE FROM messages WHERE conversation_id = :id"),
                {"id": conversation_id},
            )
            await self.db.execute(
                text("DELETE FROM conversations WHERE id = :id"),
                {"id": conversation_id},
            )
            await self.db.commit()
            return {"deleted": conversation_id, "status": "success"}
        except Exception as exc:
            await self.db.rollback()
            raise AppError(f"Error al eliminar la conversación: {exc}", 500) from exc

    async def resolve_tenant(self, user_id, org_id):
        if org_id in ("", "undefined"):
            org_id = None
        member_info = None
        if org_id:
            member_info = (
                (
                    await self.db.execute(
                        text("""
                    SELECT om.organization_id, t.id AS tenant_id
                    FROM organization_members om
                    JOIN tenants t ON t.organization_id = om.organization_id
                    WHERE om.user_id = :user_id
                      AND om.organization_id = :org_id
                      AND om.active = true
                      AND t.active = true
                    LIMIT 1
                    """),
                        {"user_id": user_id, "org_id": org_id},
                    )
                )
                .mappings()
                .first()
            )
        if not member_info:
            member_info = (
                (
                    await self.db.execute(
                        text("""
                    SELECT om.organization_id, t.id AS tenant_id
                    FROM organization_members om
                    JOIN tenants t ON t.organization_id = om.organization_id
                    JOIN organizations o ON o.id = om.organization_id
                    WHERE om.user_id = :user_id
                      AND om.active = true
                      AND t.active = true
                      AND o.active = true
                    ORDER BY CASE WHEN lower(o.name) = lower(:global_name) THEN 0 ELSE 1 END,
                             o.name
                    LIMIT 1
                    """),
                        {"user_id": user_id, "global_name": "AgroTech"},
                    )
                )
                .mappings()
                .first()
            )
        if not member_info:
            raise AppError("El usuario no tiene un Tenant activo asignado.", 403)
        return member_info

    async def ensure_conversation(self, conversation_id, tenant_id, user_id, kb_id, title):
        if conversation_id is None:
            conversation_id = str(uuid4())
            await self.db.execute(
                text("""
                INSERT INTO conversations (id, tenant_id, user_id, knowledge_base_id, title)
                VALUES (:id, :tenant_id, :user, :kb_id, :title)
                """),
                {
                    "id": conversation_id,
                    "tenant_id": tenant_id,
                    "user": user_id,
                    "kb_id": kb_id,
                    "title": title[:80],
                },
            )
        return conversation_id

    async def insert_message(self, conversation_id, role: str, content: str) -> str:
        message_id = str(uuid4())
        await self.db.execute(
            text("""
            INSERT INTO messages (id, conversation_id, role, content)
            VALUES (:id, :conversation, :role, :content)
            """),
            {
                "id": message_id,
                "conversation": conversation_id,
                "role": role,
                "content": content,
            },
        )
        return message_id

    async def insert_source(self, message_id, document_id, chunk_id, score) -> None:
        await self.db.execute(
            text("""
                INSERT INTO message_sources (id, message_id, document_id, chunk_id, similarity_score)
                VALUES (:id, :message, :document, :chunk, :score)
                """),
            {
                "id": str(uuid4()),
                "message": message_id,
                "document": document_id,
                "chunk": chunk_id,
                "score": score,
            },
        )

    async def touch(self, conversation_id) -> None:
        await self.db.execute(
            text("UPDATE conversations SET updated_at = NOW() WHERE id = :id"),
            {"id": conversation_id},
        )

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()


from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ChatContainer:
    conversations: PostgresConversationRepository


def build_chat_container(db: AsyncSession) -> ChatContainer:
    return ChatContainer(conversations=PostgresConversationRepository(db))
