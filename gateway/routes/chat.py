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
import unicodedata
from models.eval import AnswerEval
from services.rag_service import RetrievalEval
from fastapi.responses import StreamingResponse
from schemas.chat import ChatRequest, ChatResponse, ContextChunk
from schemas.evaluation import (
    DatasetEvaluationRequest, DatasetEvaluationResponse, EvaluationHistoryItem,
    QuestionBankImportRequest, SimulatorSaveRequest, SimulatorSearchRequest,
)
from services import rag as rag_service
from uuid import uuid4, UUID
from .auth import get_current_user
from services.database import get_db
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from utils.tenant import get_user_tenant_id
from models.user import User
from core.test import TEST_FILE, TestQuestion, load_tests
import pandas as pd
from models.eval import AnswerEval
from models.tenant import Tenant
import os
from models.organization import Organization
import json
import csv
import hashlib
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from models.chunk import Chunk
from datetime import datetime, timezone
from services.rag_service import RAGService
from services.agentic_rag_service import (
    AgenticRAGService,
    run_hybrid_answer,
    pack_mode_side,
)
from services.farmer_context_service import build_farmer_context
from services.evaluation_metrics import (
    dataset_fingerprint as compute_dataset_fingerprint,
    ndcg_at_k,
    precision_at_k,
    reciprocal_rank,
)

router = APIRouter(prefix="/chat", tags=["Chat"])
import math
from pydantic import BaseModel
from typing import List, Optional, Dict, Literal
import time


async def evaluate_retrieval_internal(
    test, tenant_id: str, k: int = 10, collections: list[str] | None = None
):
    """Evaluate retrieval for a test question using local RAGService pipeline."""
    evaluator = RAGService()

    context_data = await evaluator.fetch_context(
        test.question, tenant_id=tenant_id, collections=collections
    )
    retrieved_docs = context_data.get("chunks", [])

    mrr_scores = [
        evaluator.calculate_mrr(keyword, retrieved_docs) for keyword in test.keywords
    ]
    ndcg_scores = [
        evaluator.calculate_ndcg(keyword, retrieved_docs, k)
        for keyword in test.keywords
    ]

    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0
    avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0
    keywords_found = sum(1 for score in mrr_scores if score > 0)
    total_keywords = len(test.keywords)
    coverage = (keywords_found / total_keywords * 100) if total_keywords else 0.0

    top_k_docs = retrieved_docs[:k]
    relevant_docs_count = 0
    for doc in top_k_docs:
        doc_text = getattr(doc, "page_content", str(doc))
        if any(keyword.lower() in doc_text.lower() for keyword in test.keywords):
            relevant_docs_count += 1

    accuracy = (relevant_docs_count / len(top_k_docs) * 100) if top_k_docs else 0.0

    return RetrievalEval(
        mrr=avg_mrr,
        ndcg=avg_ndcg,
        keywords_found=keywords_found,
        total_keywords=total_keywords,
        keyword_coverage=coverage,
        accuracy=accuracy,
    )


async def evaluate_answer_internal(
    test, tenant_id: str, collections: list[str] | None = None
):
    """Generate an answer with the RAG pipeline and evaluate it using the RAGService judge."""
    evaluator = RAGService()

    # Use the full RAG pipeline to produce answer and chunks
    rag_result = await evaluator.answer(
        test.question, tenant_id=tenant_id, collections=collections
    )
    generated_answer = rag_result.get("answer", "")
    retrieved_docs = rag_result.get("chunks", [])

    # Evaluate with the RAGService evaluator (LLM-as-judge)
    eval_result, _, _ = await evaluator.evaluate_answer(
        test.question, generated_answer, retrieved_docs,
        reference_answer=test.reference_answer,
        out_of_knowledge=getattr(test, "out_of_knowledge", False),
    )

    return eval_result, generated_answer, retrieved_docs


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

            existing = await db.execute(
                text("""
                    SELECT id
                    FROM public.retrieval_dataset
                    WHERE tenant_id = :tenant_id
                      AND lower(btrim(question)) = lower(btrim(:question))
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
                        selected_chunk_ids,
                        keywords,
                        reference_answer,
                        category,
                        flag_different_info,
                        flag_out_of_knowledge,
                        split,
                        metadata
                    )
                    VALUES (
                        :tenant_id,
                        :question,
                        NULL,
                        CAST(:selected_chunk_ids AS JSONB),
                        CAST(:keywords AS JSONB),
                        :reference_answer,
                        :category,
                        FALSE,
                        :out_of_knowledge,
                        :split,
                        CAST(:metadata AS JSONB)
                    )
                """),
                {
                    "tenant_id": tenant_id,
                    "question": question,
                    "selected_chunk_ids": json.dumps([]),
                    "keywords": json.dumps(item.keywords),
                    "reference_answer": (item.reference_answer),
                    "category": (item.category or "general"),
                    "out_of_knowledge": item.out_of_knowledge,
                    "split": item.split,
                    "metadata": json.dumps(item.metadata),
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
            detail=("Error importando banco de preguntas: " f"{str(e)}"),
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
    # 2. DATASET
    # ============================================================

    dataset_result = await db.execute(
        text("""
            SELECT
                id,
                question,
                expected_chunk_id,
                selected_chunk_ids,
                keywords,
                reference_answer,
                category,
                flag_different_info,
                flag_out_of_knowledge,
                split,
                metadata
            FROM public.retrieval_dataset
            WHERE tenant_id = :tenant_id
              AND (:split = 'all' OR split = :split)
            ORDER BY id ASC
        """),
        {
            "tenant_id": tenant_id,
            "split": request.split,
        },
    )

    dataset_records = dataset_result.mappings().all()

    if not dataset_records:
        raise HTTPException(
            status_code=400,
            detail=("No hay preguntas en " "retrieval_dataset."),
        )

    dataset_size = len(dataset_records)

    embedding_model = request.embedding_model or "qwen3-embedding:latest"
    reranker_model = request.reranker_model or "BAAI/bge-reranker-v2-m3"

    dataset_fingerprint = compute_dataset_fingerprint(dataset_records)

    # ============================================================
    # 2. CACHE CHECK
    # ============================================================
    parameters = {
        "model_name": request.model_name,
        "embedding_model": embedding_model,
        "top_k": request.top_k,
        "retrieval_k": request.retrieval_k,
        "bm25_k": request.bm25_k,
        "rrf_k": request.rrf_k,
        "candidate_k": request.candidate_k,
        "reranker_model": reranker_model,
        "reranker_batch_size": request.reranker_batch_size,
        "distance_metric": request.distance_metric,
        "similarity_strategy": request.similarity_strategy,
        "reranking_strategy": request.reranking_strategy,
        "agentic_rag_enabled": request.agentic_rag_enabled,
        "rag_strategy": request.rag_strategy,
        "evaluation_type": "retrieval",
        "dataset_fingerprint": dataset_fingerprint,
        "split": request.split,
        "evaluation_mode": request.evaluation_mode,
    }

    existing_run = await db.execute(
        text("""
            SELECT
                id,
                model_name,
                embedding_model,
                dataset_size,
                normal_questions,
                different_info_questions,
                out_of_knowledge_questions,
                recall_1,
                recall_k,
                precision_at_k,
                ndcg,
                mrr,
                false_positives,
                failures,
                duration_ms,
                status,
                parameters,
                created_at,
                artifacts_path
            FROM public.retrieval_evaluation_runs
            WHERE tenant_id = :tenant_id
              AND status = 'completed'
              AND parameters = CAST(:parameters AS JSONB)
            ORDER BY created_at DESC
            LIMIT 1
            """),
        {
            "tenant_id": tenant_id,
            "parameters": json.dumps(parameters),
        },
    )
    existing_run = existing_run.mappings().first()

    if existing_run is not None:
        result_count = await db.scalar(
            text(
                "SELECT COUNT(*) FROM public.retrieval_evaluation_results WHERE evaluation_run_id = :run_id"
            ),
            {"run_id": existing_run["id"]},
        )

        evaluated_questions = int(result_count or 0)
        pending_questions = max(0, existing_run["dataset_size"] - evaluated_questions)

        return DatasetEvaluationResponse(
            run_id=existing_run["id"],
            model_name=existing_run["model_name"],
            embedding_model=existing_run["embedding_model"],
            dataset_name="Retrieval Eval v1",
            model_date=(
                existing_run["created_at"].isoformat()
                if existing_run["created_at"] is not None
                else None
            ),
            dataset_size=existing_run["dataset_size"],
            evaluated_questions=evaluated_questions,
            pending_questions=pending_questions,
            normal_questions=existing_run["normal_questions"],
            different_info_questions=existing_run["different_info_questions"],
            out_of_knowledge_questions=existing_run["out_of_knowledge_questions"],
            recall_1=existing_run["recall_1"] or 0.0,
            recall_k=existing_run["recall_k"] or 0.0,
            precision_at_k=existing_run["precision_at_k"] or 0.0,
            ndcg=existing_run["ndcg"] or 0.0,
            mrr=existing_run["mrr"] or 0.0,
            false_positives=existing_run["false_positives"],
            failures=existing_run["failures"],
            duration_ms=existing_run["duration_ms"] or 0.0,
            status="cached",
            parameters=parameters,
            cached=True,
            created_at=(
                existing_run["created_at"].isoformat()
                if existing_run["created_at"] is not None
                else None
            ),
            artifacts_path=existing_run["artifacts_path"],
        )

    # ============================================================
    # 3. CLASIFICACIÓN
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

    # Preguntas que realmente tienen chunks relevantes
    retrieval_questions = sum(
        1
        for row in dataset_records
        if (
            not row["flag_out_of_knowledge"]
            and (row["selected_chunk_ids"] or row["expected_chunk_id"])
        )
    )

    # ============================================================
    # 4. CONFIGURACIÓN
    # ============================================================

    embedding_model = request.embedding_model or "qwen3-embedding:latest"

    reranker_model = request.reranker_model or "BAAI/bge-reranker-v2-m3"

    parameters = {
        "model_name": request.model_name,
        "embedding_model": embedding_model,
        "top_k": request.top_k,
        "retrieval_k": request.retrieval_k,
        "bm25_k": request.bm25_k,
        "rrf_k": request.rrf_k,
        "candidate_k": request.candidate_k,
        "reranker_model": reranker_model,
        "reranker_batch_size": (request.reranker_batch_size),
        "distance_metric": (request.distance_metric),
        "similarity_strategy": (request.similarity_strategy),
        "reranking_strategy": (request.reranking_strategy),
        "agentic_rag_enabled": (request.agentic_rag_enabled),
        "rag_strategy": (request.rag_strategy),
        "evaluation_type": "retrieval",
        "dataset_fingerprint": dataset_fingerprint,
        "split": request.split,
        "evaluation_mode": request.evaluation_mode,
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
                status,
                created_at
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
                'running',
                CURRENT_TIMESTAMP
            )
            RETURNING id
        """),
        {
            "tenant_id": tenant_id,
            "model_name": request.model_name,
            "embedding_model": embedding_model,
            "top_k": request.top_k,
            "retrieval_k": request.retrieval_k,
            "bm25_k": request.bm25_k,
            "rrf_k": request.rrf_k,
            "candidate_k": request.candidate_k,
            "reranker_model": reranker_model,
            "reranker_batch_size": (request.reranker_batch_size),
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
    # 6. RAG SERVICE
    # ============================================================

    evaluator = RAGService(
        model=request.model_name,
        embedding_model=embedding_model,
        retrieval_k=request.retrieval_k,
        bm25_k=request.bm25_k,
        rrf_k=request.rrf_k,
        candidate_k=request.candidate_k,
        final_k=request.top_k,
        reranker_model=reranker_model,
        reranker_batch_size=(request.reranker_batch_size),
    )

    # ============================================================
    # 7. MÉTRICAS GLOBALES
    # ============================================================

    hits_at_1 = 0
    hits_at_k = 0

    precision_sum = 0.0
    ndcg_sum = 0.0
    mrr_sum = 0.0

    keyword_mrr_sum = 0.0
    keyword_coverage_sum = 0.0

    false_positives = 0
    failures = 0
    evaluated_questions = 0
    pending_questions = 0

    try:

        # ========================================================
        # 8. EVALUAR DATASET
        # ========================================================

        for row in dataset_records:

            question_start = time.time()

            dataset_id = int(row["id"])

            question = (row["question"] or "").strip()

            different_info = bool(row["flag_different_info"])

            out_of_knowledge = bool(row["flag_out_of_knowledge"])

            # ----------------------------------------------------
            # CHUNKS RELEVANTES
            # ----------------------------------------------------

            selected_chunk_ids = row["selected_chunk_ids"] or []

            if isinstance(
                selected_chunk_ids,
                str,
            ):
                try:
                    selected_chunk_ids = json.loads(selected_chunk_ids)
                except json.JSONDecodeError:
                    selected_chunk_ids = []

            # Compatibilidad con dataset antiguo
            if not selected_chunk_ids and row["expected_chunk_id"]:
                selected_chunk_ids = [str(row["expected_chunk_id"])]

            relevant_ids = {str(chunk_id) for chunk_id in selected_chunk_ids}

            # ----------------------------------------------------
            # KEYWORDS
            # ----------------------------------------------------

            keywords = row["keywords"] or []

            if isinstance(
                keywords,
                str,
            ):
                try:
                    keywords = json.loads(keywords)
                except json.JSONDecodeError:
                    keywords = []

            # ----------------------------------------------------
            # PREGUNTA PENDIENTE
            # ----------------------------------------------------

            if not out_of_knowledge and not relevant_ids:
                pending_questions += 1
                continue

            # ----------------------------------------------------
            # RAG
            # ----------------------------------------------------

            try:

                rag_result = await evaluator.fetch_context(
                    question=question,
                    tenant_id=str(tenant_id),
                    evaluation_mode=True,
                )

            except Exception as exc:

                print(f"Error recuperando " f"'{question}': {exc}")

                failures += 1
                continue

            final_chunks = (
                rag_result.get(
                    "chunks",
                    [],
                )
                or []
            )

            candidates = (
                rag_result.get(
                    "candidates",
                    [],
                )
                or []
            )

            # ----------------------------------------------------
            # IDS Y SCORES
            # ----------------------------------------------------

            retrieved_ids = []
            retrieved_scores = []

            for chunk in final_chunks:

                metadata = (
                    getattr(
                        chunk,
                        "metadata",
                        {},
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

            # ----------------------------------------------------
            # KEYWORDS
            # ----------------------------------------------------

            keyword_mrr = calculate_keyword_mrr(
                keywords,
                final_chunks,
            )

            keyword_coverage = calculate_keyword_coverage(
                keywords,
                final_chunks,
            )

            keyword_mrr_sum += keyword_mrr
            keyword_coverage_sum += keyword_coverage

            # ====================================================
            # MÉTRICAS INDIVIDUALES
            # ====================================================

            expected_rank = None

            hit_at_1 = False
            hit_at_k = False

            reciprocal_rank = 0.0

            precision_at_k = 0.0
            ndcg = 0.0

            false_positive = False
            failure = False

            # ----------------------------------------------------
            # OUT OF KNOWLEDGE
            # ----------------------------------------------------

            if out_of_knowledge:

                if retrieved_ids:

                    false_positive = True
                    false_positives += 1

                else:

                    # Correctamente no recuperó nada.
                    hit_at_1 = True
                    hit_at_k = True

                evaluated_questions += 1

            # ----------------------------------------------------
            # NORMAL / DIFFERENT INFO
            # ----------------------------------------------------

            elif relevant_ids:

                evaluated_questions += 1

                precision_at_k = precision_at_k(
                    relevant_ids,
                    retrieved_ids,
                    request.top_k,
                )

                ndcg = ndcg_at_k(
                    relevant_ids,
                    retrieved_ids,
                    request.top_k,
                )

                reciprocal_rank = reciprocal_rank(
                    relevant_ids,
                    retrieved_ids,
                )

                precision_sum += precision_at_k

                ndcg_sum += ndcg

                mrr_sum += reciprocal_rank

                # Recall@1
                if retrieved_ids and retrieved_ids[0] in relevant_ids:
                    hit_at_1 = True
                    hits_at_1 += 1

                # Recall@K
                retrieved_at_k = set(retrieved_ids[: request.top_k])

                if retrieved_at_k.intersection(relevant_ids):
                    hit_at_k = True
                    hits_at_k += 1

                # Rank del primer relevante
                for rank, chunk_id in enumerate(
                    retrieved_ids,
                    start=1,
                ):

                    if chunk_id in relevant_ids:
                        expected_rank = rank
                        break

                if expected_rank is None:

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
            # METADATA
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
                "evaluation_type": ("retrieval"),
                "candidate_count": len(candidates),
                "final_count": len(final_chunks),
                "relevant_chunk_ids": list(relevant_ids),
                "different_info": (different_info),
                "out_of_knowledge": (out_of_knowledge),
            }

            # ====================================================
            # GENERACIÓN Y EVALUACIÓN DE RESPUESTAS
            # - RAG: generar usando los chunks ya recuperados
            # - Vanilla: generar sin contexto (no-RAG)
            # Se almacenan las evaluaciones en retrieval_metadata
            # ====================================================
            try:
                # RAG generation using existing chunks (avoid double-retrieval)
                try:
                    messages = evaluator.build_prompt(question, [], final_chunks)
                    gen_resp = evaluator.client.chat.completions.create(
                        model=request.model_name or evaluator.model,
                        messages=messages,
                    )
                    rag_generated = gen_resp.choices[0].message.content
                except Exception as ge:
                    print(f"Error generando respuesta RAG para '{question}': {ge}")
                    rag_generated = ""

                # Evaluate RAG answer via evaluator.evaluate_answer (async)
                try:
                    rag_eval_result, _, _ = await evaluator.evaluate_answer(
                        question, rag_generated, final_chunks,
                        reference_answer=row["reference_answer"],
                        out_of_knowledge=out_of_knowledge,
                    )
                except Exception as er:
                    print(f"Error evaluando respuesta RAG: {er}")
                    rag_eval_result = None

                # Vanilla (no RAG) generation
                try:
                    vanilla_resp = await evaluator.simple_chat(question)
                    vanilla_generated = vanilla_resp.get("answer", "")
                except Exception as ve:
                    print(f"Error generando respuesta Vanilla para '{question}': {ve}")
                    vanilla_generated = ""

                # Evaluate Vanilla answer
                try:
                    vanilla_eval_result, _, _ = await evaluator.evaluate_answer(
                        question, vanilla_generated, [],
                        reference_answer=row["reference_answer"],
                        out_of_knowledge=out_of_knowledge,
                    )
                except Exception as ev:
                    print(f"Error evaluando respuesta Vanilla: {ev}")
                    vanilla_eval_result = None

                def _model_to_dict(m):
                    if m is None:
                        return None
                    if hasattr(m, "model_dump"):
                        return m.model_dump()
                    if hasattr(m, "dict"):
                        return m.dict()
                    # fallback: try to convert attributes
                    return {k: getattr(m, k) for k in dir(m) if not k.startswith("_")}

                retrieval_metadata["rag_answer"] = rag_generated
                retrieval_metadata["rag_eval"] = _model_to_dict(rag_eval_result)
                retrieval_metadata["vanilla_answer"] = vanilla_generated
                retrieval_metadata["vanilla_eval"] = _model_to_dict(vanilla_eval_result)
            except Exception as e:
                print(f"Error en generación/evaluación de respuestas: {e}")

            # ====================================================
            # GUARDAR RESULTADO
            # ====================================================

            await db.execute(
                text("""
                    INSERT INTO
                    public.retrieval_evaluation_results (
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
                        retrieval_metadata,
                        precision_at_k,
                        ndcg,
                        keyword_mrr,
                        keyword_coverage
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
                        CAST(:retrieval_metadata AS JSONB),
                        :precision_at_k,
                        :ndcg,
                        :keyword_mrr,
                        :keyword_coverage
                    )
                """),
                {
                    "run_id": run_id,
                    "dataset_id": dataset_id,
                    "question": question,
                    "expected_chunk_id": (
                        str(selected_chunk_ids[0]) if selected_chunk_ids else None
                    ),
                    "retrieved_chunk_ids": (json.dumps(retrieved_ids)),
                    "retrieved_scores": (json.dumps(retrieved_scores)),
                    "expected_rank": (expected_rank),
                    "hit_at_1": hit_at_1,
                    "hit_at_k": hit_at_k,
                    "reciprocal_rank": (reciprocal_rank),
                    "false_positive": (false_positive),
                    "failure": failure,
                    "flag_different_info": (different_info),
                    "flag_out_of_knowledge": (out_of_knowledge),
                    "retrieval_latency_ms": (latency_ms),
                    "retrieval_metadata": (
                        json.dumps(
                            retrieval_metadata,
                            default=str,
                        )
                    ),
                    "precision_at_k": (precision_at_k),
                    "ndcg": ndcg,
                    "keyword_mrr": (keyword_mrr),
                    "keyword_coverage": (keyword_coverage),
                },
            )

            await db.commit()

        # ========================================================
        # 9. MÉTRICAS GLOBALES
        # ========================================================

        if evaluated_questions > 0:

            recall_1 = hits_at_1 / evaluated_questions

            recall_k = hits_at_k / evaluated_questions

            precision_at_k = precision_sum / evaluated_questions

            ndcg = ndcg_sum / evaluated_questions

            mrr = mrr_sum / evaluated_questions

        else:

            recall_1 = 0.0
            recall_k = 0.0
            precision_at_k = 0.0
            ndcg = 0.0
            mrr = 0.0

        duration_ms = (time.time() - start_time) * 1000

        # ========================================================
        # 10. ACTUALIZAR RUN
        # ========================================================

        await db.execute(
            text("""
                UPDATE
                public.retrieval_evaluation_runs
                SET
                    recall_1 = :recall_1,
                    recall_k = :recall_k,
                    precision_at_k = :precision_at_k,
                    ndcg = :ndcg,
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
                "precision_at_k": (precision_at_k),
                "ndcg": ndcg,
                "mrr": mrr,
                "false_positives": (false_positives),
                "failures": failures,
                "duration_ms": duration_ms,
            },
        )

        await db.commit()
        # ========================================================
        # 11. EXPORT CSV / MD AGGREGATES POR CATEGORÍA
        # ========================================================
        try:
            out_dir = os.path.join("storage", "evaluation_runs", f"run_{run_id}")
            os.makedirs(out_dir, exist_ok=True)

            # Recuperar filas de resultados y su metadata
            results_q = await db.execute(
                text("""
                SELECT r.dataset_id, r.question, r.retrieval_metadata, d.category,
                       r.reciprocal_rank, r.precision_at_k, r.ndcg, r.false_positive, r.failure
                FROM public.retrieval_evaluation_results r
                LEFT JOIN public.retrieval_dataset d ON d.id = r.dataset_id
                WHERE r.evaluation_run_id = :run_id
                ORDER BY r.id ASC
                """),
                {"run_id": run_id},
            )

            rows = results_q.mappings().all()

            csv_path = os.path.join(out_dir, "comparative_results.csv")
            md_path = os.path.join(out_dir, "aggregates_by_category.md")
            summary_path = os.path.join(out_dir, "summary.json")

            # CSV: filas detalladas
            with open(csv_path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    [
                        "dataset_id",
                        "category",
                        "question",
                        "reciprocal_rank",
                        "precision_at_k",
                        "ndcg",
                        "false_positive",
                        "failure",
                        "rag_accuracy",
                        "rag_completeness",
                        "rag_relevance",
                        "vanilla_accuracy",
                        "vanilla_completeness",
                        "vanilla_relevance",
                    ]
                )

                per_cat: dict[str, list[dict]] = {}

                for r in rows:
                    metadata = r["retrieval_metadata"] or {}
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except Exception:
                            metadata = {}

                    rag_eval = (metadata or {}).get("rag_eval") or {}
                    vanilla_eval = (metadata or {}).get("vanilla_eval") or {}

                    rag_acc = None
                    rag_comp = None
                    rag_rel = None

                    vanilla_acc = None
                    vanilla_comp = None
                    vanilla_rel = None

                    try:
                        rag_acc = float(rag_eval.get("accuracy")) if rag_eval else None
                        rag_comp = (
                            float(rag_eval.get("completeness")) if rag_eval else None
                        )
                        rag_rel = float(rag_eval.get("relevance")) if rag_eval else None
                    except Exception:
                        pass

                    try:
                        vanilla_acc = (
                            float(vanilla_eval.get("accuracy"))
                            if vanilla_eval
                            else None
                        )
                        vanilla_comp = (
                            float(vanilla_eval.get("completeness"))
                            if vanilla_eval
                            else None
                        )
                        vanilla_rel = (
                            float(vanilla_eval.get("relevance"))
                            if vanilla_eval
                            else None
                        )
                    except Exception:
                        pass

                    writer.writerow(
                        [
                            r["dataset_id"],
                            r["category"],
                            r["question"],
                            r["reciprocal_rank"],
                            r["precision_at_k"],
                            r["ndcg"],
                            r["false_positive"],
                            r["failure"],
                            rag_acc,
                            rag_comp,
                            rag_rel,
                            vanilla_acc,
                            vanilla_comp,
                            vanilla_rel,
                        ]
                    )

                    per_cat.setdefault(r["category"] or "unknown", []).append(
                        {
                            "reciprocal_rank": r["reciprocal_rank"],
                            "precision_at_k": r["precision_at_k"],
                            "ndcg": r["ndcg"],
                            "rag_accuracy": rag_acc,
                            "rag_completeness": rag_comp,
                            "rag_relevance": rag_rel,
                            "vanilla_accuracy": vanilla_acc,
                            "vanilla_completeness": vanilla_comp,
                            "vanilla_relevance": vanilla_rel,
                        }
                    )

            # Markdown aggregates
            with open(md_path, "w", encoding="utf-8") as fh:
                fh.write("# Aggregates by Category\n\n")
                for cat, items in per_cat.items():
                    cnt = len(items)
                    fh.write(f"## {cat} ({cnt} samples)\n\n")

                    def avg(field):
                        vals = [i[field] for i in items if i.get(field) is not None]
                        return sum(vals) / len(vals) if vals else 0.0

                    fh.write("| Metric | RAG (avg) | Vanilla (avg) |\n")
                    fh.write("|---|---:|---:|\n")
                    fh.write(
                        f"| Reciprocal Rank | {avg('reciprocal_rank'):.3f} | {avg('reciprocal_rank'):.3f} |\n"
                    )
                    fh.write(
                        f"| Precision@K | {avg('precision_at_k'):.3f} | {avg('precision_at_k'):.3f} |\n"
                    )
                    fh.write(f"| nDCG | {avg('ndcg'):.3f} | {avg('ndcg'):.3f} |\n")
                    fh.write(f"| Rag Accuracy | {avg('rag_accuracy'):.3f} | - |\n")
                    fh.write(
                        f"| Vanilla Accuracy | - | {avg('vanilla_accuracy'):.3f} |\n\n"
                    )

            summary = {
                "run_id": run_id,
                "dataset_fingerprint": dataset_fingerprint,
                "dataset_size": dataset_size,
                "evaluated_questions": evaluated_questions,
                "pending_questions": pending_questions,
                "metrics": {
                    "recall_at_1": recall_1,
                    "recall_at_k": recall_k,
                    "precision_at_k": precision_at_k,
                    "mrr": mrr,
                    "ndcg": ndcg,
                    "false_positives": false_positives,
                    "failures": failures,
                    "duration_ms": duration_ms,
                },
                "parameters": parameters,
            }
            with open(summary_path, "w", encoding="utf-8") as fh:
                json.dump(summary, fh, ensure_ascii=False, indent=2)

            print(f"Wrote evaluation artifacts to {out_dir}")
            # Persist artifacts path to the run row
            try:
                await db.execute(
                    text(
                        "UPDATE public.retrieval_evaluation_runs SET artifacts_path = :path WHERE id = :run_id"
                    ),
                    {"path": out_dir, "run_id": run_id},
                )
                await db.commit()
            except Exception as e:
                print(f"Error persisting artifacts path: {e}")
        except Exception as e:
            print(f"Error writing evaluation artifacts: {e}")

        # ========================================================
        # 12. RESPUESTA
        # ========================================================

        # Fetch created_at and artifacts_path for response
        created_at = None
        artifacts_path = None
        try:
            run_row = await db.execute(
                text(
                    "SELECT created_at, artifacts_path FROM public.retrieval_evaluation_runs WHERE id = :run_id"
                ),
                {"run_id": run_id},
            )
            run_row = run_row.mappings().first()
            if run_row:
                created_at = run_row.get("created_at")
                artifacts_path = run_row.get("artifacts_path")
        except Exception as e:
            print(f"Error fetching run metadata: {e}")

        return DatasetEvaluationResponse(
            run_id=run_id,
            model_name=request.model_name,
            embedding_model=embedding_model,
            dataset_name="Retrieval Eval v1",
            model_date=(created_at.isoformat() if created_at is not None else None),
            dataset_size=dataset_size,
            evaluated_questions=(evaluated_questions),
            pending_questions=(pending_questions),
            normal_questions=(normal_questions),
            different_info_questions=(different_info_questions),
            out_of_knowledge_questions=(out_of_knowledge_questions),
            recall_1=recall_1,
            recall_k=recall_k,
            precision_at_k=(precision_at_k),
            ndcg=ndcg,
            mrr=mrr,
            false_positives=(false_positives),
            failures=failures,
            duration_ms=duration_ms,
            status="completed",
            parameters=parameters,
            cached=False,
            created_at=(created_at.isoformat() if created_at is not None else None),
            artifacts_path=artifacts_path,
        )

    except Exception as exc:

        await db.rollback()

        duration_ms = (time.time() - start_time) * 1000

        try:

            await db.execute(
                text("""
                    UPDATE
                    public.retrieval_evaluation_runs
                    SET
                        duration_ms = :duration_ms,
                        status = 'failed',
                        error_message = :error_message,
                        finished_at =
                            CURRENT_TIMESTAMP
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
            detail=("Error ejecutando " "la evaluación: " f"{str(exc)}"),
        )


@router.get("/evaluation/history", response_model=list[EvaluationHistoryItem])
async def get_evaluation_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await get_user_tenant_id(current_user.id, db)

    try:
        result = await db.execute(
            text("""
                SELECT
                    id,
                    created_at,
                    model_name,
                    embedding_model,
                    dataset_size,
                    top_k,
                    recall_1,
                    recall_k,
                    mrr,
                    false_positives,
                    failures,
                    duration_ms,
                    status,
                    parameters
                FROM public.retrieval_evaluation_runs
                WHERE tenant_id = :tenant_id
                ORDER BY created_at DESC
                LIMIT 20
                """),
            {"tenant_id": tenant_id},
        )
        return [dict(row) for row in result.mappings().all()]
    except Exception:
        # Tabla/columnas de evaluación aún no migradas en este entorno.
        await db.rollback()
        return []


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


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        # 1. Tenant vía organización seleccionada (AgroTech por defecto si aplica)
        GLOBAL_ORG_NAME = "AgroTech"
        org_id = getattr(request, "organization_id", None) or None
        if org_id in ("", "undefined"):
            org_id = None

        member_info = None
        if org_id:
            member_info = (
                (
                    await db.execute(
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
                        {"user_id": current_user.id, "org_id": org_id},
                    )
                )
                .mappings()
                .first()
            )

        if not member_info:
            # Preferir AgroTech si el usuario es miembro
            member_info = (
                (
                    await db.execute(
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
                        {
                            "user_id": current_user.id,
                            "global_name": GLOBAL_ORG_NAME,
                        },
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

        # 3. RAG — Hybrid / Agentic / Compare (comparación controlada TFM)
        rag_mode = (request.rag_mode or "hybrid").lower()
        if not request.use_rag:
            rag_mode = "none"

        farmer_ctx = await build_farmer_context(
            db,
            user_id=str(current_user.id),
            crop_id=request.crop_id,
            organization_id=request.organization_id,
            fallback_crop=request.crop or "platano_canarias",
            fallback_island=request.island or "La_Palma",
        )
        island = farmer_ctx["island_code"]
        crop = farmer_ctx["product_id"]
        farmer_markdown = farmer_ctx["markdown"]
        farmer_profile = farmer_ctx["profile"]
        org_name = request.organization_name or "AgroTech"

        comparison_payload = None
        agent_trace = None
        architecture = None
        core_rag = RAGService()

        if rag_mode == "none":
            rag_result = await core_rag.simple_chat(
                request.question, history=request.history
            )
            rag_result["retrieval_details"] = None
            architecture = "no_rag"
        elif rag_mode == "agentic":
            agentic = AgenticRAGService(rag=core_rag)
            rag_result = await agentic.answer(
                request.question,
                tenant_id=str(tenant_id),
                collections=[str(kb_id)] if kb_id else None,
                model=selected_model,
                history=request.history,
                island=island,
                crop=crop,
                organization_name=org_name,
                farmer_context=farmer_markdown,
                farmer_profile=farmer_profile,
            )
            architecture = rag_result.get("architecture")
            agent_trace = rag_result.get("agent_trace")
        elif rag_mode == "compare":
            agentic = AgenticRAGService(rag=core_rag)
            hybrid_result = await run_hybrid_answer(
                core_rag,
                request.question,
                tenant_id=str(tenant_id),
                collections=[str(kb_id)] if kb_id else None,
                model=selected_model,
                history=request.history,
                use_reranking=request.use_reranking,
                use_query_rewrite=request.use_query_rewrite,
                farmer_context=farmer_markdown,
                farmer_profile=farmer_profile,
            )
            agentic_result = await agentic.answer(
                request.question,
                tenant_id=str(tenant_id),
                collections=[str(kb_id)] if kb_id else None,
                model=selected_model,
                history=request.history,
                island=island,
                crop=crop,
                organization_name=org_name,
                farmer_context=farmer_markdown,
                farmer_profile=farmer_profile,
            )
            comparison_payload = {
                "hybrid": pack_mode_side(hybrid_result, "hybrid"),
                "agentic": pack_mode_side(agentic_result, "agentic"),
                "note": (
                    "Comparación controlada: misma pregunta, mismo modelo/tenant/KB. "
                    "Hybrid = Dense+BM25+RRF; Agentic = herramientas KB/clima/precios/perfil."
                ),
            }
            # Respuesta principal (conversación): Hybrid como baseline
            rag_result = hybrid_result
            architecture = "compare_hybrid_vs_agentic"
            agent_trace = agentic_result.get("agent_trace")
        else:
            # hybrid (default)
            rag_result = await run_hybrid_answer(
                core_rag,
                request.question,
                tenant_id=str(tenant_id),
                collections=[str(kb_id)] if kb_id else None,
                model=selected_model,
                history=request.history,
                use_reranking=request.use_reranking,
                use_query_rewrite=request.use_query_rewrite,
                farmer_context=farmer_markdown,
                farmer_profile=farmer_profile,
            )
            architecture = rag_result.get("architecture")

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
            retrieval_details=rag_result.get("retrieval_details"),
            related_questions=rag_result.get("related_questions") or [],
            rag_mode=rag_mode if rag_mode != "none" else "none",
            architecture=architecture,
            agent_trace=agent_trace,
            comparison=comparison_payload,
            farmer_profile=rag_result.get("farmer_profile") or farmer_profile,
        )

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluation/retrieval/{test_id}")
async def evaluate_retrieval_route(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    organization_id: UUID | None = None,
    knowledge_base_id: UUID | None = None,
):
    tests = load_tests()
    if test_id < 0 or test_id >= len(tests):
        raise HTTPException(status_code=404, detail="Test no encontrado")

    tenant_id = await get_user_tenant_id(
        current_user.id, db, organization_id=organization_id
    )
    test = tests[test_id]
    collections = [str(knowledge_base_id)] if knowledge_base_id else None

    # Ejecutar evaluación de recuperación (Retrieval) usando lógica local
    result = await evaluate_retrieval_internal(
        test, str(tenant_id), collections=collections
    )

    retrieval_data = result.model_dump() if hasattr(result, "model_dump") else result

    return {
        "test_id": test_id,
        "question": test.question,
        "category": test.category,
        "organization_id": str(organization_id) if organization_id else None,
        "knowledge_base_id": str(knowledge_base_id) if knowledge_base_id else None,
        "retrieval": retrieval_data,
    }


@router.post("/evaluation/answer/{test_id}")
async def evaluate_answer_route(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    organization_id: UUID | None = None,
    knowledge_base_id: UUID | None = None,
):
    tests = load_tests()
    if test_id < 0 or test_id >= len(tests):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test no encontrado (ID: {test_id})",
        )

    tenant_id = await get_user_tenant_id(
        current_user.id, db, organization_id=organization_id
    )
    test = tests[test_id]
    collections = [str(knowledge_base_id)] if knowledge_base_id else None

    # Ejecutar evaluación de generación (Answer) usando lógica local
    eval_result, generated_answer, chunks = await evaluate_answer_internal(
        test, str(tenant_id), collections=collections
    )

    eval_data = (
        eval_result.model_dump() if hasattr(eval_result, "model_dump") else eval_result
    )

    return {
        "test_id": test_id,
        "question": test.question,
        "category": getattr(test, "category", "general"),
        "organization_id": str(organization_id) if organization_id else None,
        "knowledge_base_id": str(knowledge_base_id) if knowledge_base_id else None,
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


@router.post("/evaluation/upload-tests")
async def upload_tests(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a JSON/JSONL file with test questions and replace the current tests file.

    The file may be a JSON array or JSONL (one JSON per line). It will be saved
    to the evaluation/tests.jsonl path used by the loader.
    """
    tenant_id = await get_user_tenant_id(current_user.id, db)

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except Exception:
        text = content.decode("latin-1")

    # Normalize to JSONL lines
    try:
        parsed = json.loads(text)
        # If parsed is a list, convert to lines
        if isinstance(parsed, list):
            lines = [json.dumps(item, ensure_ascii=False) for item in parsed]
        else:
            # single object -> one line
            lines = [json.dumps(parsed, ensure_ascii=False)]
    except Exception:
        # Try to assume it's already JSONL
        lines = [l for l in text.splitlines() if l.strip()]

    canonical_rows = []
    seen_questions = set()
    for line in lines:
        try:
            row = json.loads(line)
            item = TestQuestion(**row)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Dataset inválido: {exc}")
        key = " ".join(item.question.casefold().split())
        if key in seen_questions:
            continue
        seen_questions.add(key)
        canonical_rows.append(item.model_dump())

    tests_path = os.path.normpath(os.path.abspath(str(TEST_FILE)))
    try:
        os.makedirs(os.path.dirname(tests_path), exist_ok=True)
        with open(tests_path, "w", encoding="utf-8") as fh:
            for row in canonical_rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"No se pudo guardar el fichero de tests: {e}"
        )

    return {"status": "ok", "uploaded": len(canonical_rows), "path": tests_path}


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

    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="La pregunta no puede estar vacía.",
        )

    if not request.flags.out_of_knowledge and not request.selected_chunk_ids:
        raise HTTPException(
            status_code=400,
            detail="Debes seleccionar al menos un chunk relevante.",
        )

    try:

        await db.execute(
            text("""
                INSERT INTO public.retrieval_dataset (
                    tenant_id,
                    question,
                    expected_chunk_id,
                    selected_chunk_ids,
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
                    CAST(:selected_chunk_ids AS JSONB),
                    CAST(:keywords AS JSONB),
                    :reference_answer,
                    :category,
                    :different_info,
                    :out_of_knowledge
                )
            """),
            {
                "tenant_id": tenant_id,
                "question": request.question.strip(),
                # Compatibilidad con código antiguo.
                "expected_chunk_id": (
                    request.selected_chunk_ids[0]
                    if request.selected_chunk_ids
                    else None
                ),
                "selected_chunk_ids": json.dumps(request.selected_chunk_ids),
                "keywords": json.dumps(request.keywords),
                "reference_answer": request.reference_answer,
                "category": (request.category if request.category else "general"),
                "different_info": (request.flags.different_info),
                "out_of_knowledge": (request.flags.out_of_knowledge),
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
            detail=f"Error guardando pregunta: {str(e)}",
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

    rag_result = await rag_service.fetch_context(
        question=request.question,
        tenant_id=str(tenant_id),
        collections=[request.knowledge_base_id] if request.knowledge_base_id else None,
        evaluation_mode=request.evaluation_mode,
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


@router.post("/retrieve")
async def retrieve_pipeline(
    request: SimulatorSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Endpoint rápido para exponer los detalles de retrieval inmediatamente.

    Esto permite al frontend mostrar las fuentes y preguntas relacionadas
    antes de la generación completa del LLM.
    """
    tenant_id = await get_user_tenant_id(current_user.id, db)

    # Reutiliza el singleton del servicio; no recarga el cross-encoder.
    retrieval = await rag_service.fetch_context(
        question=request.question,
        tenant_id=str(tenant_id),
        collections=[request.knowledge_base_id] if request.knowledge_base_id else None,
        evaluation_mode=request.evaluation_mode,
    )

    return retrieval


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
            eval_result, generated_answer, _ = await evaluate_answer_internal(
                test, str(tenant_id)
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
