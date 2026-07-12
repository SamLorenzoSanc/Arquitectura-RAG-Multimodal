from fastapi import APIRouter, Depends, HTTPException, status
from schemas.chat import ChatRequest, ChatResponse, ContextChunk
from services import rag_service
from uuid import uuid4
from .auth import get_current_user 
from services.database import get_db 
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Obtenemos el Tenant asignado a este usuario a través de su organización activa
        member_info = db.execute(
            text("""
            SELECT om.organization_id, t.id as tenant_id 
            FROM organization_members om
            JOIN tenants t ON t.organization_id = om.organization_id
            WHERE om.user_id = :user_id AND om.active = true AND t.active = true
            LIMIT 1
            """),
            {"user_id": current_user["id"]}
        ).mappings().first()

        if not member_info:
            raise HTTPException(status_code=403, detail="El usuario no tiene un Tenant activo asignado.")

        tenant_id = member_info["tenant_id"]
        conversation_id = request.conversation_id

        # 1. Crear conversación si no existe (incluyendo tenant_id)
        if conversation_id is None:
            conversation_id = str(uuid4())
            # Si el request no pasa knowledge_base_id, buscamos la predeterminada del Tenant
            kb_id = request.knowledge_base_id
            if not kb_id:
                kb = db.execute(
                    text("SELECT id FROM knowledge_bases WHERE tenant_id = :tenant_id LIMIT 1"),
                    {"tenant_id": tenant_id}
                ).first()
                kb_id = kb[0] if kb else None

            db.execute(
                text("""
                INSERT INTO conversations (id, tenant_id, user_id, knowledge_base_id, title)
                VALUES (:id, :tenant_id, :user, :kb_id, :title)
                """),
                {
                    "id": conversation_id,
                    "tenant_id": tenant_id,
                    "user": current_user["id"],
                    "kb_id": kb_id,
                    "title": request.question[:80]
                }
            )
            db.commit()
        user_message_id = str(uuid4())
        db.execute(
            text("""
            INSERT INTO messages (id, conversation_id, role, content)
            VALUES (:id, :conversation, 'user', :content)
            """),
            {
                "id": user_message_id,
                "conversation": conversation_id,
                "content": request.question
            }
        )
        db.commit()
        print("Question: ", request.question)
        print("History: ", request.history)

        # 3. Llamada al servicio de RAG
        answer, chunks = rag_service.answer(
            question=request.question,
            history=request.history
        )

        # 4. Insertar respuesta del asistente
        assistant_message_id = str(uuid4())
        db.execute(
            text("""
            INSERT INTO messages (id, conversation_id, role, content)
            VALUES (:id, :conversation, 'assistant', :content)
            """),
            {
                "id": assistant_message_id,
                "conversation": conversation_id,
                "content": answer
            }
        )

        # 5. Guardar fuentes (message_sources) asociadas al documento del nuevo modelo
        for chunk in chunks:
            metadata = getattr(chunk, "metadata", {}) or chunk.get("metadata", {})
            
            db.execute(
                text("""
                INSERT INTO message_sources (id, message_id, document_id, chunk_id, similarity_score)
                VALUES (:id, :message, :document, :chunk, :score)
                """),
                {
                    "id": str(uuid4()),
                    "message": assistant_message_id,
                    "document": metadata.get("document_id"),
                    "chunk": metadata.get("chunk_id"),
                    "score": metadata.get("score")
                }
            )

        # 6. Actualizar timestamp de la conversación
        db.execute(
            text("""
            UPDATE conversations
            SET updated_at = NOW()
            WHERE id = :id
            """),
            {"id": conversation_id}
        )
        db.commit()

        # 7. Formatear salida para Pydantic
        contextos_validados = []
        for chunk in chunks:
            page_content = getattr(chunk, "page_content", "") or chunk.get("page_content", "")
            tipo_contexto = getattr(chunk, "type", "general") or chunk.get("type", "general")
            metadata_original = getattr(chunk, "metadata", {}) or chunk.get("metadata", {})
            
            contextos_validados.append(
                ContextChunk(
                    page_content=page_content,
                    type=tipo_contexto,
                    metadata=metadata_original 
                )
            )

        return ChatResponse(
            conversation_id=conversation_id,
            answer=answer,
            context=contextos_validados
        )
    
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = db.execute(
        text("""
        SELECT id, title, created_at, updated_at 
        FROM conversations 
        WHERE id = :id AND user_id = :user_id
        """),
        {"id": conversation_id, "user_id": current_user["id"]}
    ).mappings().first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    messages = db.execute(
        text("""
        SELECT id, role, content, created_at 
        FROM messages 
        WHERE conversation_id = :conversation_id
        ORDER BY created_at ASC
        """),
        {"conversation_id": conversation_id}
    ).mappings().all()

    messages_list = [
        {"id": str(msg["id"]), "role": msg["role"], "content": msg["content"]} 
        for msg in messages
    ]

    return {
        "conversation_id": str(conversation["id"]),
        "title": conversation["title"],
        "messages": messages_list
    }

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = db.execute(
        text("SELECT id FROM conversations WHERE id = :id AND user_id = :user_id"),
        {"id": conversation_id, "user_id": current_user["id"]}
    ).mappings().first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada o sin permisos")

    try:
        db.execute(
            text("""
            DELETE FROM message_sources 
            WHERE message_id IN (SELECT id FROM messages WHERE conversation_id = :id)
            """),
            {"id": conversation_id}
        )
        db.execute(text("DELETE FROM messages WHERE conversation_id = :id"), {"id": conversation_id})
        db.execute(text("DELETE FROM conversations WHERE id = :id"), {"id": conversation_id})
        db.commit()
        
        return {"deleted": conversation_id, "status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar la conversación: {str(e)}")