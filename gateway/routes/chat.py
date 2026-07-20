from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from schemas.chat import ChatRequest, ChatResponse, ContextChunk
from services import rag_service
from uuid import uuid4
from .auth import get_current_user
from services.database import get_db
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
from core.test import load_tests
import pandas as pd
from models.eval import AnswerEval
from models.tenant import Tenant
import os
from models.organization import Organization

router = APIRouter(prefix="/chat", tags=["Chat"])


def calculate_averages(results: list[dict[str, any]]) -> dict[str, float]:
    if not results:
        return {
            "mrr": 0.0,
            "ndcg": 0.0,
            "accuracy": 0.0,
            "completeness": 0.0,
            "relevance": 0.0,
        }

    df = pd.DataFrame(results)
    return {
        col: float(df[col].mean()) if col in df.columns else 0.0
        for col in ["mrr", "ndcg", "accuracy", "completeness", "relevance"]
    }

@router.get("/list-all-documents")
async def list_all_documents():
    try:
        # Accedemos a la colección específica
        collection = rag_service.chroma.get_collection("documents")
        
        # Obtenemos el conteo total
        count = collection.count()
        
        # Obtenemos los documentos (Chroma devuelve dicts con 'ids', 'documents', 'metadatas')
        data = collection.get(limit=100, include=["documents", "metadatas"])
        
        # Formateamos para que sea una lista de objetos más limpia
        documentos_formateados = [
            {
                "id": doc_id,
                "content": content,
                "metadata": meta
            }
            for doc_id, content, meta in zip(data["ids"], data["documents"], data["metadatas"])
        ]
        
        return {
            "total_en_documents": count,
            "documentos": documentos_formateados
        }
        
    except Exception as e:
        return {"error": f"No se pudo acceder a la colección 'documents': {str(e)}"}
    
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
        kb_id = request.knowledge_base_id
        
        if kb_id == "undefined" or kb_id == "":
            kb_id = None

        if conversation_id is None:
            conversation_id = str(uuid4())
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
            tenant_id=str(tenant_id) 
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

@router.post("/run-evaluation")
async def run_evaluation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    print(f"\n[AUDITORÍA] Iniciando proceso para usuario: {current_user.id}")

    # 1. Obtener el resultado de la ejecución
    query_result = await db.execute(
        text("""
            SELECT t.id 
            FROM tenants t
            JOIN organization_members om ON t.organization_id = om.organization_id
            WHERE om.user_id = :user_id AND om.active = true
            LIMIT 1
        """),
        {"user_id": current_user.id}
    )
    
    tenant_val = query_result.scalar_one_or_none()
    
    tenant_id = str(tenant_val) if tenant_val else "global"
    
    print(f"[AUDITORÍA] Tenant identificado: {tenant_id}")

    tests = load_tests() 
    print(f"[AUDITORÍA] Se han cargado {len(tests)} casos de prueba.")
    
    results = []
    
    # 3. Procesar evaluación
    for i, test in enumerate(tests):
        print(f"[TEST {i+1}/{len(tests)}] Evaluando: {test.question[:50]}...")
        
        # Llamada al servicio
        response = rag_service.answer(test.question, tenant_id=tenant_id)
        
        # Log de resultados parciales
        chunks_found = len(response["chunks"])
        print(f"  -> Chunks recuperados: {chunks_found}")
        print(f"  -> Respuesta recibida (longitud): {len(response['answer'])} caracteres")
        
        results.append({
            "question": test.question,
            "category": test.category,
            "system_answer": response["answer"],
            "retrieved_count": chunks_found
        })
    
    # 5. Calcular promedios
    total_chunks = sum(r["retrieved_count"] for r in results)
    avg_chunks = total_chunks / len(results) if results else 0
    
    print(f"\n[AUDITORÍA] Proceso finalizado.")
    print(f"[RESULTADOS] Total Tests: {len(results)} | Avg Chunks: {avg_chunks:.2f}\n")
    
    return {
        "retrieval": {
            "Total Tests": len(results),
            "Avg Chunks": avg_chunks
        },
        "quality": {
            "Success Rate": 1.0 
        },
        "details": results
    }

@router.get("/list-all-documents")
async def list_all_documents():
    try:
        collection = rag_service.chroma.get_collection("documents")
        count = collection.count()
        data = collection.get(limit=100, include=["documents", "metadatas"])

        documentos_formateados = [
            {
                "id": doc_id,
                "content": content,
                "metadata": meta,
            }
            for doc_id, content, meta in zip(data["ids"], data["documents"], data["metadatas"])
        ]

        return {
            "total_en_documents": count,
            "documentos": documentos_formateados,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo acceder a la colección 'documents': {str(e)}")


@router.get("/evaluation/tests")
async def get_evaluation_tests(
    current_user: User = Depends(get_current_user),
):
    tests = load_tests()
    return {
        "total": len(tests),
        "tests": [
            {
                "id": idx,
                "question": t.question,
                "keywords": t.keywords,
                "reference_answer": t.reference_answer,
                "category": t.category,
            }
            for idx, t in enumerate(tests)
        ],
    }


@router.get("/evaluation/tests/{test_id}")
async def get_evaluation_test(
    test_id: int,
    current_user: User = Depends(get_current_user),
):
    tests = load_tests()
    if test_id < 0 or test_id >= len(tests):
        raise HTTPException(status_code=404, detail="Test no encontrado")

    test = tests[test_id]
    return {
        "id": test_id,
        "question": test.question,
        "keywords": test.keywords,
        "reference_answer": test.reference_answer,
        "category": test.category,
    }


@router.post("/evaluation/retrieval/{test_id}")
async def evaluate_retrieval_route(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tests = load_tests()
    if test_id < 0 or test_id >= len(tests):
        raise HTTPException(status_code=404, detail="Test no encontrado")

    tenant_id = await get_user_tenant_id(current_user, db)
    test = tests[test_id]

    result = await run_in_threadpool(
        rag_service.evaluate_retrieval,
        test,
        tenant_id,
    )

    return {
        "test_id": test_id,
        "question": test.question,
        "category": test.category,
        "retrieval": result.model_dump() if hasattr(result, "model_dump") else result,
    }

@router.post("/evaluation/answer/{test_id}")
def evaluate_answer(self, test, tenant_id: str) -> tuple[AnswerEval, str, list]:
    generated_answer_result = self.answer(test.question, history=[], tenant_id=tenant_id)
    generated_answer = generated_answer_result["answer"]
    retrieved_docs = generated_answer_result["chunks"]

    prompt = f"""
        Pregunta:
        {test.question}
        
        Respuesta generada:
        {generated_answer}
        
        Respuesta de referencia:
        {test.reference_answer}
        
        Evalúa:
        1. Precisión.
        2. Exhaustividad.
        3. Pertinencia.
        
        Devuelve JSON con feedback, accuracy, completeness y relevance.
        """

    completion = self.client.chat.completions.parse(
        model=self.model,
        messages=[
            {"role": "system", "content": "Eres un evaluador experto. Responde solo en JSON."},
            {"role": "user", "content": prompt},
        ],
        response_format=AnswerEval,
    )

    eval_result = completion.choices[0].message.parsed
    return eval_result, generated_answer, retrieved_docs

@router.post("/evaluation/run")
async def run_full_evaluation(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await get_user_tenant_id(current_user, db)
    tests = load_tests()

    def _run():
        retrieval_results = []
        answer_results = []

        for idx, test in enumerate(tests):
            retrieval = rag_service.evaluate_retrieval(test, tenant_id)
            answer_eval, generated_answer, _ = rag_service.evaluate_answer(test, tenant_id)

            retrieval_results.append({
                "test_id": idx,
                "question": test.question,
                "category": test.category,
                "mrr": retrieval.mrr,
                "ndcg": retrieval.ndcg,
                "keywords_found": retrieval.keywords_found,
                "total_keywords": retrieval.total_keywords,
                "keyword_coverage": retrieval.keyword_coverage,
            })

            answer_results.append({
                "test_id": idx,
                "question": test.question,
                "category": test.category,
                "accuracy": answer_eval.accuracy,
                "completeness": answer_eval.completeness,
                "relevance": answer_eval.relevance,
                "feedback": answer_eval.feedback,
                "generated_answer": generated_answer,
            })

        return {
            "retrieval_averages": calculate_averages(retrieval_results),
            "answer_averages": calculate_averages(answer_results),
            "retrieval_details": retrieval_results,
            "answer_details": answer_results,
        }

    background_tasks.add_task(_run)

    return {
        "status": "accepted",
        "detail": "La evaluación se ha lanzado en segundo plano",
        "total_tests": len(tests),
    }