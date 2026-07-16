from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from schemas.chat import ChatRequest, ChatResponse, ContextChunk
from services import rag_service
from uuid import uuid4
from .auth import get_current_user
from services.database import get_db
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        # Tenant del usuario vía su organización activa
        member_info = (
            await db.execute(
                text("""
                SELECT om.organization_id, t.id AS tenant_id
                FROM organization_members om
                JOIN tenants t ON t.organization_id = om.organization_id
                WHERE om.user_id = :user_id AND om.active = true AND t.active = true
                LIMIT 1
                """),
                {"user_id": current_user.id},
            )
        ).mappings().first()

        if not member_info:
            raise HTTPException(status_code=403, detail="El usuario no tiene un Tenant activo asignado.")

        tenant_id = member_info["tenant_id"]
        conversation_id = request.conversation_id

        # 1. Crear conversación si no existe
        if conversation_id is None:
            conversation_id = str(uuid4())
            kb_id = request.knowledge_base_id
            if not kb_id:
                kb_id = await db.scalar(
                    text("SELECT id FROM knowledge_bases WHERE tenant_id = :tenant_id LIMIT 1"),
                    {"tenant_id": tenant_id},
                )

            await db.execute(
                text("""
                INSERT INTO conversations (id, tenant_id, user_id, knowledge_base_id, title)
                VALUES (:id, :tenant_id, :user, :kb_id, :title)
                """),
                {
                    "id": conversation_id,
                    "tenant_id": tenant_id,
                    "user": current_user.id,
                    "kb_id": kb_id,
                    "title": request.question[:80],
                },
            )

        # 2. Mensaje del usuario
        user_message_id = str(uuid4())
        await db.execute(
            text("""
            INSERT INTO messages (id, conversation_id, role, content)
            VALUES (:id, :conversation, 'user', :content)
            """),
            {"id": user_message_id, "conversation": conversation_id, "content": request.question},
        )
        # commit único de la conversación + mensaje de usuario
        await db.commit()

        # 3. RAG — bloqueante: fuera del event loop
        rag_result = await run_in_threadpool(
            rag_service.answer,
            question=request.question,
        history=request.history,
        )

        answer = rag_result["answer"]
        chunks = rag_result["chunks"]
        retrieval = rag_result["retrieval"]

        # 4. Respuesta del asistente
        assistant_message_id = str(uuid4())
        await db.execute(
            text("""
            INSERT INTO messages (id, conversation_id, role, content)
            VALUES (:id, :conversation, 'assistant', :content)
            """),
            {"id": assistant_message_id, "conversation": conversation_id, "content": answer},
        )

        # 5. Fuentes utilizadas
        for chunk in chunks:
            metadata = getattr(chunk, "metadata", None)
            if metadata is None and isinstance(chunk, dict):
                metadata = chunk.get("metadata", {})
            metadata = metadata or {}

            await db.execute(
                text("""
                INSERT INTO message_sources (id, message_id, document_id, chunk_id, similarity_score)
                VALUES (:id, :message, :document, :chunk, :score)
                """),
                {
                    "id": str(uuid4()),
                    "message": assistant_message_id,
                    "document": metadata.get("document_id"),
                    "chunk": metadata.get("chunk_id"),
                    "score": metadata.get("score"),
                },
            )

        # 6. Timestamp de la conversación
        await db.execute(
            text("UPDATE conversations SET updated_at = NOW() WHERE id = :id"),
            {"id": conversation_id},
        )
        await db.commit()

        # 7. Salida Pydantic
        contextos_validados = []
        for chunk in chunks:
            page_content = getattr(chunk, "page_content", None)
            tipo_contexto = getattr(chunk, "type", None)
            metadata_original = getattr(chunk, "metadata", None)
            if isinstance(chunk, dict):
                page_content = page_content or chunk.get("page_content", "")
                tipo_contexto = tipo_contexto or chunk.get("type", "general")
                metadata_original = metadata_original or chunk.get("metadata", {})

            contextos_validados.append(
                ContextChunk(
                    page_content=page_content or "",
                    type=tipo_contexto or "general",
                    metadata=metadata_original or {},
                )
            )

        return ChatResponse(
            conversation_id=conversation_id,
            answer=answer,
            context=contextos_validados,
            retrieval=retrieval,
        )

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations")
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    conversations = (
        await db.execute(
            text("""
            SELECT 
                id,
                title,
                created_at,
                updated_at
            FROM conversations
            WHERE user_id = :user_id
            ORDER BY updated_at DESC
            """),
            {
                "user_id": current_user.id
            },
        )
    ).mappings().all()


    return [
        {
            "id": str(conv["id"]),
            "title": conv["title"],
            "created_at": conv["created_at"],
            "updated_at": conv["updated_at"],
        }
        for conv in conversations
    ]

@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = (
        await db.execute(
            text("""
            SELECT id, title, created_at, updated_at
            FROM conversations
            WHERE id = :id AND user_id = :user_id
            """),
            {"id": conversation_id, "user_id": current_user.id},
        )
    ).mappings().first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    messages = (
        await db.execute(
            text("""
            SELECT id, role, content, created_at
            FROM messages
            WHERE conversation_id = :conversation_id
            ORDER BY created_at ASC
            """),
            {"conversation_id": conversation_id},
        )
    ).mappings().all()

    messages_list = [
        {"id": str(msg["id"]), "role": msg["role"], "content": msg["content"]}
        for msg in messages
    ]

    return {
        "conversation_id": str(conversation["id"]),
        "title": conversation["title"],
        "messages": messages_list,
    }


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = (
        await db.execute(
            text("SELECT id FROM conversations WHERE id = :id AND user_id = :user_id"),
            {"id": conversation_id, "user_id": current_user.id},
        )
    ).mappings().first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada o sin permisos")

    try:
        await db.execute(
            text("""
            DELETE FROM message_sources
            WHERE message_id IN (SELECT id FROM messages WHERE conversation_id = :id)
            """),
            {"id": conversation_id},
        )
        await db.execute(text("DELETE FROM messages WHERE conversation_id = :id"), {"id": conversation_id})
        await db.execute(text("DELETE FROM conversations WHERE id = :id"), {"id": conversation_id})
        await db.commit()
        return {"deleted": conversation_id, "status": "success"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar la conversación: {str(e)}")
