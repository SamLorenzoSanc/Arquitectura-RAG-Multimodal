from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends,
    BackgroundTasks,
    status,
)
from models.eval import AnswerEval
from services.rag_service import RetrievalEval
from fastapi.responses import StreamingResponse
from schemas.chat import ChatRequest, ChatResponse, ContextChunk
from services import rag_service
from uuid import uuid4
from .auth import get_current_user
from services.database import get_db
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from utils.tenant import get_user_tenant_id
from models.user import User
from core.test import load_tests
import pandas as pd
from models.eval import AnswerEval
from models.tenant import Tenant
import os
from models.organization import Organization
import json
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from services.tool import agent_executor
import json
from models.chunk import Chunk
from datetime import datetime, timezone
from services.rag_service import RAGService

router = APIRouter(prefix="/chat", tags=["Chat"])

from pydantic import BaseModel
from typing import List, Optional, Dict
import time


class QuestionBankItem(BaseModel):
    question: str
    keywords: list[str] = []
    reference_answer: str | None = None
    category: str = "general"


class QuestionBankImportRequest(BaseModel):
    questions: list[QuestionBankItem]


class SimulatorSearchRequest(BaseModel):
    question: str


class SimulatorFlags(BaseModel):
    different_info: bool = False
    out_of_knowledge: bool = False


class DatasetEvaluationRequest(BaseModel):
    model_name: str = "llama3.2"
    embedding_model: str = "qwen3-embedding:latest"
    top_k: int = 5
    retrieval_k: int = 10
    bm25_k: int = 10
    rrf_k: int = 60
    candidate_k: int = 15
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_batch_size: int = 16


class DatasetEvaluationResponse(BaseModel):
    run_id: int
    model_name: str
    embedding_model: str
    dataset_size: int
    normal_questions: int
    different_info_questions: int
    out_of_knowledge_questions: int
    recall_1: float
    recall_k: float
    mrr: float
    false_positives: int
    failures: int
    duration_ms: float
    status: str
    parameters: dict


class SimulatorSaveRequest(BaseModel):
    question: str
    selected_chunk_id: str
    flags: SimulatorFlags

    keywords: list[str] = []
    reference_answer: str | None = None
    category: str = "general"


class EvaluationHistoryItem(BaseModel):
    id: int
    created_at: str
    model_name: str
    embedding_model: str
    dataset_size: int
    top_k: int
    recall_1: float
    recall_k: float
    mrr: float
    false_positives: int
    failures: int
    duration_ms: float
    status: str


class EvaluationResultItem(BaseModel):
    id: int
    dataset_id: int
    question: str
    expected_chunk_id: str | None
    retrieved_chunk_ids: list[str]
    retrieved_scores: list[float]
    expected_rank: int | None
    hit_at_1: bool
    hit_at_k: bool
    reciprocal_rank: float
    false_positive: bool
    failure: bool
    flag_different_info: bool
    flag_out_of_knowledge: bool
    retrieval_latency_ms: float | None


def normalize_text(value: str) -> str:
    import unicodedata

    value = value.lower().strip()

    value = unicodedata.normalize(
        "NFD",
        value,
    )

    value = "".join(c for c in value if unicodedata.category(c) != "Mn")

    return value


def calculate_keyword_mrr(
    keywords: list[str],
    chunks: list,
) -> float:

    if not keywords:
        return 0.0

    scores = []

    for keyword in keywords:

        rank_found = None

        for rank, chunk in enumerate(
            chunks,
            start=1,
        ):
            content = getattr(
                chunk,
                "page_content",
                "",
            )

            if keyword_found(
                keyword,
                content,
            ):
                rank_found = rank
                break

        scores.append(1.0 / rank_found if rank_found else 0.0)

    return sum(scores) / len(scores)


def calculate_keyword_coverage(
    keywords: list[str],
    chunks: list,
) -> float:

    if not keywords:
        return 0.0

    full_text = "\n".join(
        getattr(
            chunk,
            "page_content",
            "",
        )
        for chunk in chunks
    )

    found = sum(
        1
        for keyword in keywords
        if keyword_found(
            keyword,
            full_text,
        )
    )

    return found / len(keywords)


def keyword_found(
    keyword: str,
    text: str,
) -> bool:

    return normalize_text(keyword) in normalize_text(text)


def calculate_averages(results: list[dict[str, any]]) -> dict[str, float]:
    if not results:
        return {
            "mrr": 0.0,
            "ndcg": 0.0,
            "precision": 0.0,
            "accuracy": 0.0,
            "completeness": 0.0,
            "relevance": 0.0,
            "false_positives": 0.0,
        }

    sums = {}
    count = len(results)
    for res in results:
        for key, val in res.items():
            if isinstance(val, (int, float)):
                sums[key] = sums.get(key, 0.0) + val

    return {k: v / count for k, v in sums.items() if isinstance(v, (int, float))}


@router.get("/list-all-documents")
async def list_all_documents(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Chunk).order_by(Chunk.position))

    chunks = result.scalars().all()

    return {
        "total": len(chunks),
        "documentos": [
            {
                "id": str(chunk.id),
                "document_id": str(chunk.document_id),
                "headline": chunk.headline,
                "summary": chunk.summary,
                "content": chunk.content,
            }
            for chunk in chunks
        ],
    }


@router.post("/simulator/import-question-bank")
async def import_question_bank(
    request: QuestionBankImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await get_user_tenant_id(
        current_user.id,
        db,
    )

    if not request.questions:
        raise HTTPException(
            status_code=400,
            detail="El banco de preguntas está vacío.",
        )

    imported = 0
    skipped = 0

    try:
        for item in request.questions:

            question = item.question.strip()

            if not question:
                skipped += 1
                continue

            # Evitar duplicados
            existing = await db.execute(
                text("""
                    SELECT id
                    FROM public.retrieval_dataset
                    WHERE tenant_id = :tenant_id
                      AND question = :question
                    LIMIT 1
                """),
                {
                    "tenant_id": tenant_id,
                    "question": question,
                },
            )

            if existing.scalar_one_or_none() is not None:
                skipped += 1
                continue

            await db.execute(
                text("""
                    INSERT INTO public.retrieval_dataset (
                        tenant_id,
                        question,
                        expected_chunk_id,
                        keywords,
                        reference_answer,
                        category,
                        flag_different_info,
                        flag_out_of_knowledge
                    )
                    VALUES (
                        :tenant_id,
                        :question,
                        NULL,
                        CAST(:keywords AS JSONB),
                        :reference_answer,
                        :category,
                        FALSE,
                        FALSE
                    )
                """),
                {
                    "tenant_id": tenant_id,
                    "question": question,
                    "keywords": json.dumps(item.keywords),
                    "reference_answer": item.reference_answer,
                    "category": item.category,
                },
            )

            imported += 1

        await db.commit()

        return {
            "status": "success",
            "imported": imported,
            "skipped": skipped,
            "total": len(request.questions),
        }

    except Exception as e:
        await db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Error importando banco de preguntas: {str(e)}",
        )


@router.post(
    "/simulator/evaluate-dataset",
    response_model=DatasetEvaluationResponse,
)
async def evaluate_dataset(
    request: DatasetEvaluationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Evalúa TODO el retrieval_dataset utilizando exactamente
    el mismo RAGService que utiliza la aplicación.

    NO genera respuestas de llama3.2.

    Evalúa:

        question
            ↓
        RAGService.fetch_context()
            ↓
        Dense + BM25
            ↓
        RRF
            ↓
        Cross-Encoder
            ↓
        top_k
            ↓
        expected_chunk_id

    Métricas:

        Recall@1
        Recall@K
        MRR
        False Positives
        Failures

    Además almacena:

        retrieval_evaluation_runs
        retrieval_evaluation_results
    """

    start_time = time.time()

    tenant_id = await get_user_tenant_id(
        current_user.id,
        db,
    )

    # ============================================================
    # 1. VALIDACIÓN
    # ============================================================

    if request.top_k < 1:
        raise HTTPException(
            status_code=400,
            detail="top_k debe ser >= 1",
        )

    if request.retrieval_k < request.top_k:
        raise HTTPException(
            status_code=400,
            detail="retrieval_k debe ser >= top_k",
        )

    if request.bm25_k < 1:
        raise HTTPException(
            status_code=400,
            detail="bm25_k debe ser >= 1",
        )

    if request.candidate_k < request.top_k:
        raise HTTPException(
            status_code=400,
            detail="candidate_k debe ser >= top_k",
        )

    # ============================================================
    # 2. LEER DATASET
    # ============================================================

    dataset_result = await db.execute(
        text("""
            SELECT
                id,
                question,
                expected_chunk_id,
                flag_different_info,
                flag_out_of_knowledge,
                created_at
            FROM public.retrieval_dataset
            WHERE tenant_id = :tenant_id
            ORDER BY id ASC
            """),
        {
            "tenant_id": tenant_id,
        },
    )

    dataset_records = dataset_result.mappings().all()

    for row in dataset_records:
        keywords = row["keywords"] or []

        if isinstance(keywords, str):
            keywords = json.loads(keywords)

        reference_answer = row["reference_answer"]
        category = row["category"]

    if not dataset_records:
        raise HTTPException(
            status_code=400,
            detail=("No hay preguntas en retrieval_dataset " "para este tenant."),
        )

    dataset_size = len(dataset_records)

    # ============================================================
    # 3. CLASIFICACIÓN DEL DATASET
    # ============================================================

    normal_questions = sum(
        1
        for row in dataset_records
        if not row["flag_different_info"] and not row["flag_out_of_knowledge"]
    )

    different_info_questions = sum(
        1 for row in dataset_records if row["flag_different_info"]
    )

    out_of_knowledge_questions = sum(
        1 for row in dataset_records if row["flag_out_of_knowledge"]
    )

    # Preguntas que tienen un expected_chunk_id
    # y por tanto participan en Recall/MRR.
    retrieval_questions = sum(
        1
        for row in dataset_records
        if not row["flag_out_of_knowledge"] and row["expected_chunk_id"]
    )

    # ============================================================
    # 4. CONFIGURACIÓN DEL EXPERIMENTO
    # ============================================================

    parameters = {
        "model_name": request.model_name,
        "embedding_model": request.embedding_model,
        "top_k": request.top_k,
        "retrieval_k": request.retrieval_k,
        "bm25_k": request.bm25_k,
        "rrf_k": request.rrf_k,
        "candidate_k": request.candidate_k,
        "reranker_model": request.reranker_model,
        "reranker_batch_size": request.reranker_batch_size,
        "evaluation_type": "retrieval",
        "rag_service": "RAGService.fetch_context",
    }

    # ============================================================
    # 5. CREAR RUN
    # ============================================================

    run_result = await db.execute(
        text("""
            INSERT INTO public.retrieval_evaluation_runs (
                tenant_id,
                model_name,
                embedding_model,
                top_k,
                retrieval_k,
                bm25_k,
                rrf_k,
                candidate_k,
                reranker_model,
                reranker_batch_size,
                dataset_size,
                normal_questions,
                different_info_questions,
                out_of_knowledge_questions,
                parameters,
                status
            )
            VALUES (
                :tenant_id,
                :model_name,
                :embedding_model,
                :top_k,
                :retrieval_k,
                :bm25_k,
                :rrf_k,
                :candidate_k,
                :reranker_model,
                :reranker_batch_size,
                :dataset_size,
                :normal_questions,
                :different_info_questions,
                :out_of_knowledge_questions,
                CAST(:parameters AS JSONB),
                'running'
            )
            RETURNING id
            """),
        {
            "tenant_id": tenant_id,
            "model_name": request.model_name,
            "embedding_model": request.embedding_model,
            "top_k": request.top_k,
            "retrieval_k": request.retrieval_k,
            "bm25_k": request.bm25_k,
            "rrf_k": request.rrf_k,
            "candidate_k": request.candidate_k,
            "reranker_model": request.reranker_model,
            "reranker_batch_size": request.reranker_batch_size,
            "dataset_size": dataset_size,
            "normal_questions": normal_questions,
            "different_info_questions": (different_info_questions),
            "out_of_knowledge_questions": (out_of_knowledge_questions),
            "parameters": json.dumps(parameters),
        },
    )

    run_id = run_result.scalar_one()

    await db.commit()

    # ============================================================
    # 6. CREAR RAG SERVICE
    # ============================================================

    evaluator = RAGService(
        model=request.model_name,
        embedding_model=request.embedding_model,
        retrieval_k=request.retrieval_k,
        bm25_k=request.bm25_k,
        rrf_k=request.rrf_k,
        candidate_k=request.candidate_k,
        final_k=request.top_k,
        reranker_model=request.reranker_model,
        reranker_batch_size=request.reranker_batch_size,
    )

    # ============================================================
    # 7. MÉTRICAS
    # ============================================================

    hits_at_1 = 0
    hits_at_k = 0
    mrr_sum = 0.0

    false_positives = 0
    failures = 0

    try:

        # ========================================================
        # 8. EVALUAR CADA PREGUNTA
        # ========================================================

        for row in dataset_records:

            question_start = time.time()

            dataset_id = int(row["id"])

            question = (row["question"] or "").strip()

            expected_chunk_id = (
                str(row["expected_chunk_id"]) if row["expected_chunk_id"] else None
            )

            different_info = bool(row["flag_different_info"])

            out_of_knowledge = bool(row["flag_out_of_knowledge"])

            # ----------------------------------------------------
            # Llamada al RAG REAL
            # ----------------------------------------------------

            rag_result = await evaluator.fetch_context(
                question=question,
                tenant_id=str(tenant_id),
            )

            # ----------------------------------------------------
            # Chunks finales
            # ----------------------------------------------------

            final_chunks = rag_result.get("chunks", []) or []

            keyword_mrr = calculate_keyword_mrr(
                keywords,
                final_chunks,
            )

            keyword_coverage = calculate_keyword_coverage(
                keywords,
                final_chunks,
            )

            # ----------------------------------------------------
            # Candidatos antes del reranker
            # ----------------------------------------------------

            candidates = (
                rag_result.get(
                    "candidates",
                    [],
                )
                or []
            )

            # ----------------------------------------------------
            # IDs finales
            # ----------------------------------------------------

            retrieved_ids = []
            retrieved_scores = []

            for chunk in final_chunks:

                metadata = (
                    getattr(
                        chunk,
                        "metadata",
                        None,
                    )
                    or {}
                )

                chunk_id = metadata.get("chunk_id")

                if not chunk_id:
                    continue

                retrieved_ids.append(str(chunk_id))

                score = metadata.get("cross_encoder_score")

                if score is None:
                    score = metadata.get(
                        "rrf_score",
                        0.0,
                    )

                try:
                    score = float(score)
                except (
                    TypeError,
                    ValueError,
                ):
                    score = 0.0

                retrieved_scores.append(score)

            # ====================================================
            # MÉTRICAS DE ESTA PREGUNTA
            # ====================================================

            expected_rank = None

            hit_at_1 = False
            hit_at_k = False

            reciprocal_rank = 0.0

            false_positive = False
            failure = False

            # ----------------------------------------------------
            # OUT OF KNOWLEDGE
            # ----------------------------------------------------

            if out_of_knowledge:

                # Una pregunta OOK NO tiene expected chunk.
                #
                # Si el RAG devuelve chunks, tenemos un
                # falso positivo.
                #
                # Si no devuelve ninguno, es correcto.
                if retrieved_ids:
                    false_positive = True
                    false_positives += 1

            # ----------------------------------------------------
            # PREGUNTA CON EXPECTED CHUNK
            # ----------------------------------------------------

            elif expected_chunk_id:

                try:

                    expected_rank = retrieved_ids.index(expected_chunk_id) + 1

                    # Recall@1
                    if expected_rank == 1:
                        hit_at_1 = True
                        hits_at_1 += 1

                    # Recall@K
                    if expected_rank <= request.top_k:
                        hit_at_k = True
                        hits_at_k += 1

                    # MRR
                    reciprocal_rank = 1.0 / expected_rank

                    mrr_sum += reciprocal_rank

                except ValueError:

                    failure = True
                    failures += 1

            # ----------------------------------------------------
            # DATASET MAL FORMADO
            # ----------------------------------------------------

            else:

                failure = True
                failures += 1

            # ====================================================
            # LATENCIA
            # ====================================================

            latency_ms = (time.time() - question_start) * 1000

            # ====================================================
            # METADATA DEL RAG
            # ====================================================

            retrieval_metadata = (
                rag_result.get(
                    "retrieval",
                    {},
                )
                or {}
            )

            retrieval_metadata = {
                **retrieval_metadata,
                "evaluation_type": "retrieval",
                "candidate_count": len(candidates),
                "final_count": len(final_chunks),
                "expected_chunk_id": (expected_chunk_id),
                "different_info": (different_info),
                "out_of_knowledge": (out_of_knowledge),
            }

            # ====================================================
            # GUARDAR RESULTADO INDIVIDUAL
            # ====================================================

            await db.execute(
                text("""
                    INSERT INTO public.retrieval_evaluation_results (
                        evaluation_run_id,
                        dataset_id,
                        question,
                        expected_chunk_id,
                        retrieved_chunk_ids,
                        retrieved_scores,
                        expected_rank,
                        hit_at_1,
                        hit_at_k,
                        reciprocal_rank,
                        false_positive,
                        failure,
                        flag_different_info,
                        flag_out_of_knowledge,
                        retrieval_latency_ms,
                        retrieval_metadata
                    )
                    VALUES (
                        :run_id,
                        :dataset_id,
                        :question,
                        :expected_chunk_id,
                        CAST(:retrieved_chunk_ids AS JSONB),
                        CAST(:retrieved_scores AS JSONB),
                        :expected_rank,
                        :hit_at_1,
                        :hit_at_k,
                        :reciprocal_rank,
                        :false_positive,
                        :failure,
                        :flag_different_info,
                        :flag_out_of_knowledge,
                        :retrieval_latency_ms,
                        CAST(:retrieval_metadata AS JSONB)
                    )
                    """),
                {
                    "run_id": run_id,
                    "dataset_id": dataset_id,
                    "question": question,
                    "expected_chunk_id": (expected_chunk_id),
                    "retrieved_chunk_ids": json.dumps(retrieved_ids),
                    "retrieved_scores": json.dumps(retrieved_scores),
                    "expected_rank": expected_rank,
                    "hit_at_1": hit_at_1,
                    "hit_at_k": hit_at_k,
                    "reciprocal_rank": (reciprocal_rank),
                    "false_positive": (false_positive),
                    "failure": failure,
                    "flag_different_info": (different_info),
                    "flag_out_of_knowledge": (out_of_knowledge),
                    "retrieval_latency_ms": (latency_ms),
                    "retrieval_metadata": json.dumps(
                        retrieval_metadata,
                        default=str,
                    ),
                },
            )

            # Commit por pregunta.
            await db.commit()

        # ========================================================
        # 9. MÉTRICAS GLOBALES
        # ========================================================

        if retrieval_questions > 0:

            recall_1 = hits_at_1 / retrieval_questions

            recall_k = hits_at_k / retrieval_questions

            mrr = mrr_sum / retrieval_questions

        else:

            recall_1 = 0.0
            recall_k = 0.0
            mrr = 0.0

        duration_ms = (time.time() - start_time) * 1000

        # ========================================================
        # 10. ACTUALIZAR RUN
        # ========================================================

        await db.execute(
            text("""
                UPDATE public.retrieval_evaluation_runs
                SET
                    recall_1 = :recall_1,
                    recall_k = :recall_k,
                    mrr = :mrr,
                    false_positives = :false_positives,
                    failures = :failures,
                    duration_ms = :duration_ms,
                    status = 'completed',
                    finished_at = CURRENT_TIMESTAMP
                WHERE id = :run_id
                """),
            {
                "run_id": run_id,
                "recall_1": recall_1,
                "recall_k": recall_k,
                "mrr": mrr,
                "false_positives": (false_positives),
                "failures": failures,
                "duration_ms": duration_ms,
            },
        )

        await db.commit()

        # ========================================================
        # 11. RESPUESTA
        # ========================================================

        return DatasetEvaluationResponse(
            run_id=run_id,
            model_name=request.model_name,
            embedding_model=request.embedding_model,
            dataset_size=dataset_size,
            normal_questions=(normal_questions),
            different_info_questions=(different_info_questions),
            out_of_knowledge_questions=(out_of_knowledge_questions),
            recall_1=recall_1,
            recall_k=recall_k,
            mrr=mrr,
            false_positives=(false_positives),
            failures=failures,
            duration_ms=duration_ms,
            status="completed",
            parameters=parameters,
        )

    except Exception as exc:

        # ========================================================
        # ERROR
        # ========================================================

        await db.rollback()

        duration_ms = (time.time() - start_time) * 1000

        try:

            await db.execute(
                text("""
                    UPDATE public.retrieval_evaluation_runs
                    SET
                        duration_ms = :duration_ms,
                        status = 'failed',
                        error_message = :error_message,
                        finished_at = CURRENT_TIMESTAMP
                    WHERE id = :run_id
                    """),
                {
                    "run_id": run_id,
                    "duration_ms": duration_ms,
                    "error_message": str(exc)[:4000],
                },
            )

            await db.commit()

        except Exception:
            await db.rollback()

        raise HTTPException(
            status_code=500,
            detail=("Error ejecutando la evaluación: " f"{str(exc)}"),
        )


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        # 1. Tenant del usuario vía su organización activa (Aislamiento Multi-Tenant)
        member_info = (
            (
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
            )
            .mappings()
            .first()
        )

        if not member_info:
            raise HTTPException(
                status_code=403, detail="El usuario no tiene un Tenant activo asignado."
            )

        tenant_id = member_info["tenant_id"]
        conversation_id = request.conversation_id
        kb_id = request.knowledge_base_id

        # Extracción del modelo de lenguaje gratuito seleccionado en el frontend (Ollama)
        selected_model = getattr(request, "model", None) or "llama3.2:latest"

        if kb_id == "undefined" or kb_id == "":
            kb_id = None

        if conversation_id is None:
            conversation_id = str(uuid4())
            if not kb_id:
                kb_id = await db.scalar(
                    text(
                        "SELECT id FROM knowledge_bases WHERE tenant_id = :tenant_id LIMIT 1"
                    ),
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

        # 2. Guardar mensaje del usuario
        user_message_id = str(uuid4())
        await db.execute(
            text("""
            INSERT INTO messages (id, conversation_id, role, content)
            VALUES (:id, :conversation, 'user', :content)
            """),
            {
                "id": user_message_id,
                "conversation": conversation_id,
                "content": request.question,
            },
        )
        await db.commit()

        # 3. RAG — Llamada directa usando await
        rag_result = await rag_service.answer(
            question=request.question,
            history=request.history,
            tenant_id=str(tenant_id),
            model=selected_model,
        )

        answer = rag_result["answer"]
        chunks = rag_result["chunks"]
        retrieval = rag_result["retrieval"]

        # 4. Guardar respuesta del asistente
        assistant_message_id = str(uuid4())
        await db.execute(
            text("""
            INSERT INTO messages (id, conversation_id, role, content)
            VALUES (:id, :conversation, 'assistant', :content)
            """),
            {
                "id": assistant_message_id,
                "conversation": conversation_id,
                "content": answer,
            },
        )

        # 5. Registrar fuentes utilizadas (Chunks)
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

        # 6. Actualizar timestamp de la conversación
        await db.execute(
            text("UPDATE conversations SET updated_at = NOW() WHERE id = :id"),
            {"id": conversation_id},
        )
        await db.commit()

        # 7. Mapeo a Pydantic
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


@router.post("/simulator/import-question-bank")
async def import_question_bank(
    request: QuestionBankImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await get_user_tenant_id(
        current_user.id,
        db,
    )

    if not request.questions:
        raise HTTPException(
            status_code=400,
            detail="El banco de preguntas está vacío.",
        )

    imported = 0
    skipped = 0

    try:
        for item in request.questions:

            question = item.question.strip()

            if not question:
                skipped += 1
                continue

            # Evitar duplicados
            existing = await db.execute(
                text("""
                    SELECT id
                    FROM public.retrieval_dataset
                    WHERE tenant_id = :tenant_id
                      AND question = :question
                    LIMIT 1
                """),
                {
                    "tenant_id": tenant_id,
                    "question": question,
                },
            )

            if existing.scalar_one_or_none() is not None:
                skipped += 1
                continue

            await db.execute(
                text("""
                    INSERT INTO public.retrieval_dataset (
                        tenant_id,
                        question,
                        expected_chunk_id,
                        keywords,
                        reference_answer,
                        category,
                        flag_different_info,
                        flag_out_of_knowledge
                    )
                    VALUES (
                        :tenant_id,
                        :question,
                        NULL,
                        CAST(:keywords AS JSONB),
                        :reference_answer,
                        :category,
                        FALSE,
                        FALSE
                    )
                """),
                {
                    "tenant_id": tenant_id,
                    "question": question,
                    "keywords": json.dumps(item.keywords),
                    "reference_answer": item.reference_answer,
                    "category": item.category,
                },
            )

            imported += 1

        await db.commit()

        return {
            "status": "success",
            "imported": imported,
            "skipped": skipped,
            "total": len(request.questions),
        }

    except Exception as e:
        await db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Error importando banco de preguntas: {str(e)}",
        )


@router.get("/conversations")
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    conversations = (
        (
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
                {"user_id": current_user.id},
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
        for conv in conversations
    ]


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = (
        (
            await db.execute(
                text("""
            SELECT id, title, created_at, updated_at
            FROM conversations
            WHERE id = :id AND user_id = :user_id
            """),
                {"id": conversation_id, "user_id": current_user.id},
            )
        )
        .mappings()
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    messages = (
        (
            await db.execute(
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
        (
            await db.execute(
                text(
                    "SELECT id FROM conversations WHERE id = :id AND user_id = :user_id"
                ),
                {"id": conversation_id, "user_id": current_user.id},
            )
        )
        .mappings()
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=404, detail="Conversación no encontrada o sin permisos"
        )

    try:
        await db.execute(
            text("""
            DELETE FROM message_sources
            WHERE message_id IN (SELECT id FROM messages WHERE conversation_id = :id)
            """),
            {"id": conversation_id},
        )
        await db.execute(
            text("DELETE FROM messages WHERE conversation_id = :id"),
            {"id": conversation_id},
        )
        await db.execute(
            text("DELETE FROM conversations WHERE id = :id"), {"id": conversation_id}
        )
        await db.commit()
        return {"deleted": conversation_id, "status": "success"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al eliminar la conversación: {str(e)}"
        )


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

    tenant_id = await get_user_tenant_id(current_user.id, db)
    test = tests[test_id]

    # Ejecutar evaluación de recuperación (Retrieval)
    result = await rag_service.evaluate_retrieval(test, str(tenant_id))

    retrieval_data = result.model_dump() if hasattr(result, "model_dump") else result

    return {
        "test_id": test_id,
        "question": test.question,
        "category": test.category,
        "retrieval": retrieval_data,
    }


@router.post("/evaluation/answer/{test_id}")
async def evaluate_answer_route(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tests = load_tests()
    if test_id < 0 or test_id >= len(tests):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test no encontrado (ID: {test_id})",
        )

    tenant_id = await get_user_tenant_id(current_user.id, db)
    test = tests[test_id]

    # Ejecutar evaluación de generación (Answer)
    eval_result, generated_answer, chunks = await rag_service.evaluate_answer(
        test=test,
        tenant_id=str(tenant_id),
    )

    eval_data = (
        eval_result.model_dump() if hasattr(eval_result, "model_dump") else eval_result
    )

    return {
        "test_id": test_id,
        "question": test.question,
        "category": getattr(test, "category", "general"),
        "reference_answer": test.reference_answer,
        "generated_answer": generated_answer,
        "evaluation": eval_data,
        "retrieved_chunks": [
            {
                "content": getattr(chunk, "page_content", str(chunk)),
                "metadata": getattr(chunk, "metadata", {}),
            }
            for chunk in chunks
        ],
    }


@router.post("/simulator/evaluate-dataset", response_model=DatasetEvaluationResponse)
async def evaluate_dataset(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    3. Evalúa el dataset completo comparando el chunk esperado con los resultados reales de búsqueda.
    """
    tenant_id = await get_user_tenant_id(current_user.id, db)

    start_time = time.time()

    # 1. Obtener todas las preguntas guardadas en el dataset
    dataset_records = (
        (
            await db.execute(
                text("""
            SELECT question, expected_chunk_id, flag_different_info, flag_out_of_knowledge
            FROM public.retrieval_dataset
            WHERE tenant_id = :tenant
        """),
                {"tenant": tenant_id},
            )
        )
        .mappings()
        .all()
    )

    if not dataset_records:
        raise HTTPException(
            status_code=400, detail="El dataset está vacío. Guarda preguntas primero."
        )

    total_queries = len(dataset_records)
    hits_at_1 = 0
    hits_at_k = 0
    mrr_sum = 0.0
    false_positives = 0
    failures = 0

    K = 5  # Definimos K para Recall@K

    # 2. Iterar y evaluar cada pregunta
    for record in dataset_records:
        question = record["question"]
        expected_chunk = str(record["expected_chunk_id"])
        should_be_empty = record["flag_out_of_knowledge"]

        # Volver a realizar la búsqueda (mock, llama a tu servicio real)
        search_results = await rag_service.search_with_scores(
            question=question, tenant_id=str(tenant_id), k=K
        )

        # Extraer IDs de los chunks devueltos
        retrieved_ids = []
        for chunk, _ in search_results:
            metadata = getattr(chunk, "metadata", {})
            retrieved_ids.append(str(metadata.get("chunk_id", "")))

        # Evaluar flags: Si no debía devolver nada pero devolvió, es falso positivo
        if should_be_empty and len(retrieved_ids) > 0:
            false_positives += 1
            failures += 1
            continue

        if should_be_empty and len(retrieved_ids) == 0:
            # Caso de éxito: No devolvió nada y no debía devolver nada
            hits_at_1 += 1
            hits_at_k += 1
            mrr_sum += 1.0
            continue

        # Encontrar en qué posición (rank) aparece el esperado (1-indexed)
        try:
            rank = retrieved_ids.index(expected_chunk) + 1

            if rank == 1:
                hits_at_1 += 1
            if rank <= K:
                hits_at_k += 1

            mrr_sum += 1.0 / rank

        except ValueError:
            # El chunk esperado no se encontró entre los top K
            failures += 1

    # 3. Calcular métricas finales
    recall_1 = hits_at_1 / total_queries
    recall_k = hits_at_k / total_queries
    mrr = mrr_sum / total_queries
    duration_ms = (time.time() - start_time) * 1000

    return DatasetEvaluationResponse(
        model_date=time.strftime("%Y-%m-%d"),
        dataset_name="Retrieval Eval v1",
        recall_1=recall_1,
        recall_k=recall_k,
        mrr=mrr,
        false_positives=false_positives,
        failures=failures,
        duration_ms=duration_ms,
    )


@router.post("/simulator/save-dataset")
async def save_to_dataset(
    request: SimulatorSaveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await get_user_tenant_id(
        current_user.id,
        db,
    )

    try:

        await db.execute(
            text("""
                INSERT INTO public.retrieval_dataset (
                    tenant_id,
                    question,
                    expected_chunk_id,
                    keywords,
                    reference_answer,
                    category,
                    flag_different_info,
                    flag_out_of_knowledge
                )
                VALUES (
                    :tenant_id,
                    :question,
                    :expected_chunk_id,
                    CAST(:keywords AS JSONB),
                    :reference_answer,
                    :category,
                    :different_info,
                    :out_of_knowledge
                )
            """),
            {
                "tenant_id": tenant_id,
                "question": request.question,
                "expected_chunk_id": request.selected_chunk_id,
                "keywords": json.dumps(request.keywords),
                "reference_answer": request.reference_answer,
                "category": request.category,
                "different_info": request.flags.different_info,
                "out_of_knowledge": request.flags.out_of_knowledge,
            },
        )

        await db.commit()

        return {
            "status": "success",
            "message": "Pregunta guardada correctamente.",
        }

    except Exception as e:

        await db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.post("/simulator/search")
async def simulator_search(
    request: SimulatorSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await get_user_tenant_id(
        current_user.id,
        db,
    )

    evaluator = RAGService(
        model="llama3.2",
        embedding_model="qwen3-embedding:latest",
        retrieval_k=10,
        bm25_k=10,
        rrf_k=60,
        candidate_k=15,
        final_k=5,
        reranker_model="BAAI/bge-reranker-v2-m3",
        reranker_batch_size=16,
    )

    rag_result = await evaluator.fetch_context(
        question=request.question,
        tenant_id=str(tenant_id),
    )

    chunks = rag_result.get("chunks", []) or []

    results = []

    for rank, chunk in enumerate(chunks, start=1):

        metadata = getattr(chunk, "metadata", {}) or {}

        results.append(
            {
                "id": str(metadata.get("chunk_id")),
                "rank": rank,
                "title": metadata.get(
                    "source",
                    "Documento General",
                ),
                "description": chunk.page_content[:1000],
                "score": metadata.get(
                    "cross_encoder_score",
                    metadata.get("rrf_score", 0.0),
                ),
                "distance": metadata.get("distance"),
                "content": chunk.page_content,
            }
        )

    return {
        "question": request.question,
        "chunks": results,
        "retrieval": rag_result.get("retrieval", {}),
    }


@router.get("/evaluation/stream-run")
async def stream_evaluation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await get_user_tenant_id(current_user.id, db)
    tests = load_tests()

    async def event_generator():
        answer_results = []

        for idx, test in enumerate(tests):
            # Llamada directa usando await
            eval_result, generated_answer, _ = await rag_service.evaluate_answer(
                test=test,
                tenant_id=str(tenant_id),
            )

            # Formatear el resultado individual
            eval_dict = (
                eval_result.model_dump()
                if hasattr(eval_result, "model_dump")
                else eval_result
            )

            # Guardar para cálculo final de promedios
            answer_results.append(
                {
                    "accuracy": getattr(eval_result, "accuracy", 0.0),
                    "completeness": getattr(eval_result, "completeness", 0.0),
                    "relevance": getattr(eval_result, "relevance", 0.0),
                }
            )

            payload = {
                "done": False,
                "progress": f"{idx + 1}/{len(tests)}",
                "current": idx + 1,
                "total": len(tests),
                "test_id": idx,
                "question": test.question,
                "category": getattr(test, "category", "general"),
                "generated_answer": generated_answer,
                "evaluation": eval_dict,
            }

            # Enviar evento progresivo al frontend
            yield f"data: {json.dumps(payload)}\n\n"

        # 2. Evento final con promedios acumulados
        averages = calculate_averages(answer_results)
        final_payload = {
            "done": True,
            "progress": "Completado",
            "averages": averages,
        }
        yield f"data: {json.dumps(final_payload)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
