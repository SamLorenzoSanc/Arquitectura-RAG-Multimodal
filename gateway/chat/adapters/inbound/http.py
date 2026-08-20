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
from rag.application.evaluate import ir_from_texts, retrieval_eval_from_values
from fastapi.responses import StreamingResponse
from schemas.chat import ChatRequest, ChatResponse, ContextChunk
from schemas.evaluation import (
    DatasetEvaluationRequest,
    DatasetEvaluationResponse,
    EvaluationHistoryItem,
    ExperimentCompareRequest,
    ExperimentCompareResponse,
    ExperimentRunRequest,
    RetrievalStrategyCompareRequest,
    QuestionBankImportRequest,
    SimulatorSaveRequest,
    SimulatorSearchRequest,
)
from services import rag as rag_service
from uuid import uuid4, UUID
from routes.auth import get_current_user
from chat.composition import build_chat_container
from identity.adapters.inbound.errors import http_error
from shared.errors import AppError
from services.database import get_db
from services.human_validation import (
    init_human_validation_tables,
    queue_chat_review,
)
from services.evaluation_dataset import (
    init_retrieval_dataset_table,
    init_experiment_runs_table,
    record_experiment_run,
    safe_rollback,
)
from services.embedding_reindex import EMBEDDING_CATALOG, ensure_multi_embedding_schema
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from utils.tenant import get_user_tenant_id
from utils.knowledge_scope import (
    resolve_knowledge_collections,
    resolve_knowledge_scope,
)
from models.user import User
from core.test import TEST_FILE, TestQuestion, load_tests, merge_test_banks
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
from services.rag_service import (
    DEFAULT_BM25_K,
    DEFAULT_CANDIDATE_K,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_RETRIEVAL_K,
    EVAL_TOP_K,
    RAGService,
    RAG_TEMPERATURE,
    rag_runtime_config,
)
from services.agentic_rag_service import (
    AgenticRAGService,
    run_hybrid_answer,
    pack_mode_side,
)
from services.evaluation_metrics import (
    dataset_fingerprint as compute_dataset_fingerprint,
    keyword_ir_metrics,
    ndcg_at_k,
    normalize_text,
    precision_at_k,
    reciprocal_rank,
)

router = APIRouter(prefix="/chat", tags=["Chat"])
lab_router = APIRouter(prefix="/chat", tags=["Chat lab"])
import math
from pydantic import BaseModel
from typing import List, Optional, Dict, Literal
import time


async def evaluate_retrieval_internal(
    test,
    tenant_id: str,
    k: int = EVAL_TOP_K,
    collections: list[str] | None = None,
    distance_metric: str = "cosine",
    embedding_model: str | None = None,
    retrieval_strategy: str = "hybrid",
):
    """Evaluate retrieval for a test question using local RAGService pipeline."""
    evaluator = RAGService(
        embedding_model=embedding_model or DEFAULT_EMBEDDING_MODEL,
        retrieval_k=k,
        bm25_k=k,
        candidate_k=max(15, k),
        final_k=k,
    )

    context_data = await evaluator.fetch_context(
        test.question,
        tenant_id=tenant_id,
        collections=collections,
        evaluation_mode=True,
        distance_metric=distance_metric,
        retrieval_strategy=retrieval_strategy,
    )
    retrieved_docs = context_data.get("chunks", [])
    retrieved_ids = [
        str((getattr(doc, "metadata", {}) or {}).get("chunk_id") or "")
        for doc in retrieved_docs
    ]
    expected_ids = {
        str(item)
        for item in (getattr(test, "metadata", {}) or {}).get("expected_chunk_ids", [])
        if str(item).strip()
    }

    keywords = [str(item).strip() for item in (test.keywords or []) if str(item).strip()]
    if not keywords and not getattr(test, "out_of_knowledge", False):
        keywords = [
            token
            for token in (test.reference_answer or test.question or "").split()
            if len(token) > 4
        ][:6]

    if expected_ids:
        avg_mrr = reciprocal_rank(expected_ids, retrieved_ids)
        avg_ndcg = ndcg_at_k(expected_ids, retrieved_ids, k)
        keywords_found = sum(1 for chunk_id in retrieved_ids[:k] if chunk_id in expected_ids)
        total_keywords = len(expected_ids)
        coverage = (keywords_found / total_keywords * 100) if total_keywords else 0.0
        accuracy = precision_at_k(expected_ids, retrieved_ids, k) * 100
        return retrieval_eval_from_values(
            mrr=avg_mrr,
            ndcg=avg_ndcg,
            keywords_found=keywords_found,
            total_keywords=total_keywords,
            keyword_coverage=coverage,
            accuracy=accuracy,
        )

    texts = [
        getattr(doc, "page_content", None)
        or (doc.get("page_content") if isinstance(doc, dict) else "")
        or str(doc)
        for doc in retrieved_docs
    ]
    metrics = keyword_ir_metrics(keywords, texts, k)
    return retrieval_eval_from_values(
        mrr=float(metrics["mrr"]),
        ndcg=float(metrics["ndcg"]),
        keywords_found=int(metrics["keywords_found"]),
        total_keywords=int(metrics["total_keywords"]),
        keyword_coverage=float(metrics["keyword_coverage"]),
        accuracy=float(metrics["accuracy"]),
    )


def _expected_chunk_sql(value: str | None) -> str:
    return str(value or "").strip()


def _normalize_distance_metric(metric: str | None) -> str:
    value = (metric or "cosine").strip().lower()
    aliases = {"l1": "manhattan", "l2": "euclidean"}
    return aliases.get(value, value)


def _iso_ts(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _distance_from_parameters(parameters) -> str:
    if isinstance(parameters, str):
        try:
            parameters = json.loads(parameters)
        except json.JSONDecodeError:
            parameters = {}
    if not isinstance(parameters, dict):
        return "cosine"
    return _normalize_distance_metric(parameters.get("distance_metric") or "cosine")


async def run_question_bank_experiment(
    tests: list[TestQuestion],
    tenant_id: str,
    *,
    embedding_model: str,
    distance_metric: str,
    k: int = EVAL_TOP_K,
    collections: list[str] | None = None,
    retrieval_strategy: str = "hybrid",
) -> dict:
    """Evalúa el banco unificado con un par embedding × distancia."""
    start = time.time()
    metric = _normalize_distance_metric(distance_metric)
    mrr_sum = ndcg_sum = coverage_sum = accuracy_sum = 0.0
    hits_at_1 = hits_at_k = failures = evaluated = 0

    for test in tests:
        if getattr(test, "out_of_knowledge", False):
            try:
                evaluator = RAGService(
                    embedding_model=embedding_model or DEFAULT_EMBEDDING_MODEL,
                    retrieval_k=k,
                    bm25_k=k,
                    candidate_k=max(15, k),
                    final_k=k,
                )
                context_data = await evaluator.fetch_context(
                    test.question,
                    tenant_id,
                    collections=collections,
                    evaluation_mode=True,
                    distance_metric=metric,
                    retrieval_strategy=retrieval_strategy,
                )
                retrieved = context_data.get("chunks") or []
                evaluated += 1
                if not retrieved:
                    hits_at_1 += 1
                    hits_at_k += 1
                    mrr_sum += 1.0
                    ndcg_sum += 1.0
            except Exception:
                failures += 1
            continue
        try:
            ev = await evaluate_retrieval_internal(
                test,
                tenant_id,
                k=k,
                collections=collections,
                distance_metric=metric,
                embedding_model=embedding_model,
                retrieval_strategy=retrieval_strategy,
            )
            mrr_sum += ev.mrr
            ndcg_sum += ev.ndcg
            coverage_sum += ev.keyword_coverage
            accuracy_sum += ev.accuracy
            hits_at_1 += 1 if ev.mrr >= 0.999 else 0
            hits_at_k += 1 if ev.mrr > 0 else 0
            evaluated += 1
        except Exception:
            failures += 1

    ook = sum(1 for test in tests if getattr(test, "out_of_knowledge", False))
    in_scope = max(0, len(tests) - ook)
    n = evaluated or 1
    return {
        "dataset_size": len(tests),
        "evaluated_questions": evaluated,
        "recall_1": (hits_at_1 / evaluated) if evaluated else 0.0,
        "recall_k": (hits_at_k / evaluated) if evaluated else 0.0,
        "mrr": mrr_sum / n if evaluated else 0.0,
        "ndcg": ndcg_sum / n if evaluated else 0.0,
        "precision_at_k": (accuracy_sum / n) / 100.0 if evaluated else 0.0,
        "keyword_coverage": (coverage_sum / n) / 100.0 if evaluated else 0.0,
        "accuracy": (accuracy_sum / n) / 100.0 if evaluated else 0.0,
        "failures": failures,
        "duration_ms": (time.time() - start) * 1000,
        "parameters": {
            "embedding_model": embedding_model,
            "distance_metric": metric,
            "top_k": k,
            "collections": collections or [],
            "evaluation_type": "question_bank",
            "retrieval_strategy": retrieval_strategy,
            "temperature": RAG_TEMPERATURE,
            "in_scope": in_scope,
            "out_of_knowledge": ook,
            "dataset_label": f"{in_scope}+{ook}",
        },
    }


def _history_item_from_experiment(row: dict) -> EvaluationHistoryItem:
    parameters = row.get("parameters") or {}
    if isinstance(parameters, str):
        try:
            parameters = json.loads(parameters)
        except json.JSONDecodeError:
            parameters = {}
    top_k = EVAL_TOP_K
    if isinstance(parameters, dict):
        try:
            top_k = int(parameters.get("top_k") or EVAL_TOP_K)
        except (TypeError, ValueError):
            top_k = EVAL_TOP_K
    return EvaluationHistoryItem(
        id=int(row["id"]),
        created_at=_iso_ts(row.get("created_at")),
        model_name=row.get("generation_model") or "",
        embedding_model=row.get("embedding_model") or DEFAULT_EMBEDDING_MODEL,
        distance_metric=_normalize_distance_metric(
            row.get("distance_metric") or "cosine"
        ),
        dataset_size=int(row.get("dataset_size") or 0),
        top_k=top_k,
        recall_1=float(row.get("recall_1") or 0.0),
        recall_k=float(row.get("recall_k") or 0.0),
        precision_at_k=row.get("precision_at_k"),
        ndcg=row.get("ndcg"),
        mrr=float(row.get("mrr") or 0.0),
        keyword_coverage=row.get("keyword_coverage"),
        accuracy=row.get("accuracy"),
        false_positives=0,
        failures=int(row.get("failures") or 0),
        duration_ms=float(row.get("duration_ms") or 0.0),
        status=row.get("status") or "completed",
        experiment_type=row.get("experiment_type") or "question_bank",
        retrieval_strategy=(
            parameters.get("retrieval_strategy")
            if isinstance(parameters, dict)
            else None
        ),
        parameters=parameters if isinstance(parameters, dict) else {},
    )


async def evaluate_answer_internal(
    test,
    tenant_id: str,
    collections: list[str] | None = None,
    temperature: float | None = None,
    k: int = EVAL_TOP_K,
):
    """Genera la respuesta y evalúa retrieval + answer sobre los mismos fragmentos."""
    evaluator = RAGService(
        retrieval_k=max(DEFAULT_RETRIEVAL_K, k),
        bm25_k=max(DEFAULT_BM25_K, k),
        candidate_k=max(DEFAULT_CANDIDATE_K, k),
        final_k=k,
    )

    rag_result = await evaluator.answer(
        test.question,
        tenant_id=tenant_id,
        collections=collections,
        temperature=RAG_TEMPERATURE if temperature is None else float(temperature),
    )
    generated_answer = rag_result.get("answer", "")
    retrieved_docs = rag_result.get("chunks", [])
    keywords = [str(item).strip() for item in (test.keywords or []) if str(item).strip()]

    eval_result, _, _ = await evaluator.evaluate_answer(
        test.question,
        generated_answer,
        retrieved_docs,
        reference_answer=test.reference_answer,
        out_of_knowledge=getattr(test, "out_of_knowledge", False),
        keywords=keywords,
    )
    retrieval = ir_from_texts(
        keywords,
        [
            getattr(doc, "page_content", None)
            or (doc.get("page_content") if isinstance(doc, dict) else "")
            or str(doc)
            for doc in retrieved_docs
        ],
        k=k,
    )
    return eval_result, generated_answer, retrieved_docs, retrieval


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


def _serialize_test(index: int, test: TestQuestion) -> dict:
    metadata = test.metadata or {}
    expected_ids = metadata.get("expected_chunk_ids") or []
    return {
        "id": index,
        "question": test.question,
        "keywords": test.keywords,
        "reference_answer": test.reference_answer,
        "category": test.category,
        "split": test.split,
        "out_of_knowledge": test.out_of_knowledge,
        "different_info": bool(metadata.get("different_info")),
        "expected_chunk_ids": expected_ids,
        "source": metadata.get("source", "file"),
        "source_file": getattr(test, "source_file", "") or metadata.get("source_file") or "",
        "page": getattr(test, "page", "") or metadata.get("page") or "",
        "validated": metadata.get("validated") is not False
        if metadata.get("source") == "hitl"
        else True,
        "annotated": bool(expected_ids) or test.out_of_knowledge or bool(metadata.get("different_info")),
    }


async def load_unified_tests(
    db: AsyncSession | None = None,
    tenant_id: str | None = None,
    *,
    validated_only: bool = False,
) -> list[TestQuestion]:
    """Banco de oro (JSONL) más anotaciones HITL en retrieval_dataset."""
    file_tests = load_tests()
    if db is None or not tenant_id:
        return file_tests

    try:
        await init_retrieval_dataset_table(db)
        result = await db.execute(
            text("""
                SELECT
                    question,
                    keywords,
                    reference_answer,
                    category,
                    split,
                    flag_out_of_knowledge,
                    flag_different_info,
                    selected_chunk_ids,
                    expected_chunk_id,
                    metadata
                FROM public.retrieval_dataset
                WHERE tenant_id = :tenant_id
                ORDER BY id ASC
            """),
            {"tenant_id": tenant_id},
        )
        rows = [dict(row) for row in result.mappings().all()]
    except Exception:
        await safe_rollback(db)
        return file_tests

    tests = merge_test_banks(file_tests, rows)
    if not validated_only:
        return tests
    curated: list[TestQuestion] = []
    for item in tests:
        meta = item.metadata or {}
        if meta.get("source") == "hitl" and meta.get("validated") is False:
            continue
        curated.append(item)
    return curated


async def resolve_evaluation_tests(
    current_user: User,
    db: AsyncSession,
    organization_id: UUID | None = None,
    *,
    validated_only: bool = False,
) -> list[TestQuestion]:
    tenant_id = None
    try:
        tenant_id = await get_user_tenant_id(
            current_user.id, db, organization_id=organization_id
        )
    except Exception:
        await safe_rollback(db)
        tenant_id = None
    return await load_unified_tests(
        db, tenant_id, validated_only=validated_only
    )


@lab_router.get("/list-all-documents")
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


@lab_router.post("/simulator/import-question-bank")
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
        await init_retrieval_dataset_table(db)

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
                        :expected_chunk_id,
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
                    "expected_chunk_id": "",
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


@lab_router.post(
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

    await init_retrieval_dataset_table(db)

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

    embedding_model = request.embedding_model or DEFAULT_EMBEDDING_MODEL
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
        "temperature": getattr(request, "temperature", RAG_TEMPERATURE),
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

    if existing_run is not None and not request.force:
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

    embedding_model = request.embedding_model or DEFAULT_EMBEDDING_MODEL

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
        "temperature": getattr(request, "temperature", RAG_TEMPERATURE),
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
                    distance_metric=request.distance_metric,
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
        try:
            await record_experiment_run(
                db,
                tenant_id=str(tenant_id),
                embedding_model=embedding_model,
                distance_metric=request.distance_metric,
                generation_model=request.model_name,
                experiment_type="retrieval_dataset",
                dataset_size=dataset_size,
                evaluated_questions=evaluated_questions,
                recall_1=recall_1,
                recall_k=recall_k,
                mrr=mrr,
                ndcg=ndcg,
                precision_at_k=precision_at_k,
                keyword_coverage=None,
                accuracy=None,
                failures=failures,
                duration_ms=duration_ms,
                parameters=parameters,
            )
        except Exception as exp_exc:
            print(f"Error persistiendo experimento RAG: {exp_exc}")
            await safe_rollback(db)
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


@lab_router.get("/evaluation/history", response_model=list[EvaluationHistoryItem])
async def get_evaluation_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    organization_id: UUID | None = None,
):
    tenant_id = await get_user_tenant_id(
        current_user.id, db, organization_id=organization_id
    )

    try:
        await init_experiment_runs_table(db)
        result = await db.execute(
            text("""
                SELECT
                    id,
                    created_at,
                    generation_model,
                    embedding_model,
                    distance_metric,
                    dataset_size,
                    recall_1,
                    recall_k,
                    precision_at_k,
                    ndcg,
                    mrr,
                    keyword_coverage,
                    accuracy,
                    failures,
                    duration_ms,
                    status,
                    experiment_type,
                    parameters
                FROM public.rag_experiment_runs
                WHERE tenant_id = :tenant_id
                ORDER BY created_at DESC
                LIMIT 50
                """),
            {"tenant_id": tenant_id},
        )
        experiment_rows = [dict(row) for row in result.mappings().all()]
        if experiment_rows:
            return [_history_item_from_experiment(row) for row in experiment_rows]
    except Exception:
        await safe_rollback(db)

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
                    precision_at_k,
                    ndcg,
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
        items: list[EvaluationHistoryItem] = []
        for row in result.mappings().all():
            data = dict(row)
            items.append(
                EvaluationHistoryItem(
                    id=int(data["id"]),
                    created_at=_iso_ts(data.get("created_at")),
                    model_name=data.get("model_name") or "",
                    embedding_model=data.get("embedding_model")
                    or DEFAULT_EMBEDDING_MODEL,
                    distance_metric=_distance_from_parameters(data.get("parameters")),
                    dataset_size=int(data.get("dataset_size") or 0),
                    top_k=int(data.get("top_k") or 10),
                    recall_1=float(data.get("recall_1") or 0.0),
                    recall_k=float(data.get("recall_k") or 0.0),
                    precision_at_k=data.get("precision_at_k"),
                    ndcg=data.get("ndcg"),
                    mrr=float(data.get("mrr") or 0.0),
                    false_positives=int(data.get("false_positives") or 0),
                    failures=int(data.get("failures") or 0),
                    duration_ms=float(data.get("duration_ms") or 0.0),
                    status=data.get("status") or "completed",
                    experiment_type="retrieval_dataset",
                    parameters=(
                        data.get("parameters")
                        if isinstance(data.get("parameters"), dict)
                        else _distance_from_parameters(data.get("parameters"))
                        and {}
                    )
                    if isinstance(data.get("parameters"), dict)
                    else (
                        json.loads(data["parameters"])
                        if isinstance(data.get("parameters"), str)
                        else {}
                    ),
                )
            )
        return items
    except Exception:
        await safe_rollback(db)
        return []


@lab_router.get("/evaluation/experiments", response_model=list[EvaluationHistoryItem])
async def list_evaluation_experiments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    organization_id: UUID | None = None,
):
    return await get_evaluation_history(
        current_user, db, organization_id=organization_id
    )


@lab_router.get("/evaluation/embedding-models")
async def list_indexed_embedding_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    indexed: list[str] = []
    try:
        result = await db.execute(
            text(
                """
                SELECT DISTINCT model
                FROM public.embeddings
                WHERE model IS NOT NULL AND btrim(model) <> ''
                ORDER BY model
                """
            )
        )
        indexed = [str(row[0]) for row in result.all() if row[0]]
    except Exception:
        await safe_rollback(db)
    default = indexed[0] if indexed else DEFAULT_EMBEDDING_MODEL
    try:
        await ensure_multi_embedding_schema(db)
    except Exception:
        await safe_rollback(db)

    return {
        "indexed": indexed,
        "default": default,
        "catalog": EMBEDDING_CATALOG,
        "note": (
            "Tras reindexar el corpus con varios modelos, cada embedding vive "
            "en su propio espacio y comparar MRR/nDCG entre ellos es válido. "
            "Las distancias (coseno, L2, L1) se comparan sobre el mismo modelo."
        ),
    }


@lab_router.post("/evaluation/experiments", response_model=EvaluationHistoryItem)
async def create_evaluation_experiment(
    request: ExperimentRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    organization_id: UUID | None = None,
):
    tenant_id = await get_user_tenant_id(
        current_user.id, db, organization_id=organization_id
    )
    tests = await resolve_evaluation_tests(
        current_user, db, organization_id, validated_only=True
    )
    if not tests:
        raise HTTPException(
            status_code=400,
            detail="El banco de preguntas está vacío.",
        )
    collections = [str(request.knowledge_base_id)] if request.knowledge_base_id else None
    metrics = await run_question_bank_experiment(
        tests,
        str(tenant_id),
        embedding_model=request.embedding_model or DEFAULT_EMBEDDING_MODEL,
        distance_metric=request.distance_metric,
        k=request.top_k,
        collections=collections,
    )
    metrics.setdefault("parameters", {})["temperature"] = request.temperature
    row = {
        "id": 0,
        "created_at": datetime.now(timezone.utc),
        "generation_model": None,
        "embedding_model": request.embedding_model or DEFAULT_EMBEDDING_MODEL,
        "distance_metric": _normalize_distance_metric(request.distance_metric),
        "experiment_type": "question_bank",
        **metrics,
    }
    if request.persist:
        try:
            saved = await record_experiment_run(
                db,
                tenant_id=str(tenant_id),
                embedding_model=row["embedding_model"],
                distance_metric=row["distance_metric"],
                experiment_type="question_bank",
                dataset_size=metrics["dataset_size"],
                evaluated_questions=metrics["evaluated_questions"],
                recall_1=metrics["recall_1"],
                recall_k=metrics["recall_k"],
                mrr=metrics["mrr"],
                ndcg=metrics["ndcg"],
                precision_at_k=metrics["precision_at_k"],
                keyword_coverage=metrics["keyword_coverage"],
                accuracy=metrics["accuracy"],
                failures=metrics["failures"],
                duration_ms=metrics["duration_ms"],
                parameters=metrics["parameters"],
            )
            row["id"] = int(saved.get("id") or 0)
            row["created_at"] = saved.get("created_at") or row["created_at"]
        except Exception as exc:
            await safe_rollback(db)
            raise HTTPException(
                status_code=500,
                detail=f"No se pudo guardar la corrida: {exc}",
            ) from exc
    return _history_item_from_experiment(row)


@lab_router.post(
    "/evaluation/experiments/compare",
    response_model=ExperimentCompareResponse,
)
async def compare_evaluation_experiments(
    request: ExperimentCompareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await get_user_tenant_id(current_user.id, db)
    tests = await resolve_evaluation_tests(
        current_user, db, validated_only=True
    )
    if not tests:
        raise HTTPException(
            status_code=400,
            detail="El banco de preguntas está vacío.",
        )

    embeddings = request.embedding_models or [DEFAULT_EMBEDDING_MODEL]
    distances = request.distance_metrics or ["cosine", "euclidean", "manhattan"]
    collections = [str(request.knowledge_base_id)] if request.knowledge_base_id else None
    runs: list[EvaluationHistoryItem] = []

    for embedding_model in embeddings:
        for distance_metric in distances:
            metrics = await run_question_bank_experiment(
                tests,
                str(tenant_id),
                embedding_model=embedding_model,
                distance_metric=distance_metric,
                k=request.top_k,
                collections=collections,
            )
            row = {
                "id": 0,
                "created_at": datetime.now(timezone.utc),
                "generation_model": None,
                "embedding_model": embedding_model,
                "distance_metric": _normalize_distance_metric(distance_metric),
                "experiment_type": "distance_compare",
                **metrics,
            }
            try:
                saved = await record_experiment_run(
                    db,
                    tenant_id=str(tenant_id),
                    embedding_model=embedding_model,
                    distance_metric=_normalize_distance_metric(distance_metric),
                    experiment_type="distance_compare",
                    dataset_size=metrics["dataset_size"],
                    evaluated_questions=metrics["evaluated_questions"],
                    recall_1=metrics["recall_1"],
                    recall_k=metrics["recall_k"],
                    mrr=metrics["mrr"],
                    ndcg=metrics["ndcg"],
                    precision_at_k=metrics["precision_at_k"],
                    keyword_coverage=metrics["keyword_coverage"],
                    accuracy=metrics["accuracy"],
                    failures=metrics["failures"],
                    duration_ms=metrics["duration_ms"],
                    parameters=metrics["parameters"],
                )
                row["id"] = int(saved.get("id") or 0)
                row["created_at"] = saved.get("created_at") or row["created_at"]
            except Exception as exc:
                await safe_rollback(db)
                raise HTTPException(
                    status_code=500,
                    detail=f"No se pudo guardar la comparación: {exc}",
                ) from exc
            runs.append(_history_item_from_experiment(row))

    best = max(runs, key=lambda item: item.mrr) if runs else None
    return ExperimentCompareResponse(
        runs=runs,
        best_mrr_id=best.id if best else None,
    )


@lab_router.post(
    "/evaluation/experiments/strategies",
    response_model=ExperimentCompareResponse,
)
async def compare_retrieval_strategies(
    request: RetrievalStrategyCompareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ejecuta una ablación de estrategias sobre el mismo banco y top-k."""
    tenant_id = await get_user_tenant_id(
        current_user.id,
        db,
        organization_id=request.organization_id,
    )
    tests = await resolve_evaluation_tests(
        current_user, db, validated_only=True
    )
    if not tests:
        raise HTTPException(
            status_code=400,
            detail="El banco de preguntas está vacío.",
        )
    strategies = list(dict.fromkeys(request.strategies))
    if not strategies:
        raise HTTPException(
            status_code=422,
            detail="Selecciona al menos una estrategia de recuperación.",
        )
    if request.organization_id:
        scope = await resolve_knowledge_scope(
            db,
            user_id=current_user.id,
            organization_id=request.organization_id,
            department_id=request.department_id,
        )
        collections = await resolve_knowledge_collections(
            db,
            scope=scope,
            knowledge_base_id=request.knowledge_base_id,
        )
    else:
        collections = (
            [str(request.knowledge_base_id)]
            if request.knowledge_base_id
            else None
        )
    metric = _normalize_distance_metric(request.distance_metric)
    runs: list[EvaluationHistoryItem] = []
    for strategy in strategies:
        metrics = await run_question_bank_experiment(
            tests,
            str(tenant_id),
            embedding_model=request.embedding_model or DEFAULT_EMBEDDING_MODEL,
            distance_metric=metric,
            k=request.top_k,
            collections=collections,
            retrieval_strategy=strategy,
        )
        metrics.setdefault("parameters", {})["temperature"] = request.temperature
        row = {
            "id": 0,
            "created_at": datetime.now(timezone.utc),
            "generation_model": None,
            "embedding_model": request.embedding_model or DEFAULT_EMBEDDING_MODEL,
            "distance_metric": metric,
            "experiment_type": "retrieval_strategy",
            **metrics,
        }
        try:
            saved = await record_experiment_run(
                db,
                tenant_id=str(tenant_id),
                embedding_model=row["embedding_model"],
                distance_metric=metric,
                experiment_type="retrieval_strategy",
                dataset_size=metrics["dataset_size"],
                evaluated_questions=metrics["evaluated_questions"],
                recall_1=metrics["recall_1"],
                recall_k=metrics["recall_k"],
                mrr=metrics["mrr"],
                ndcg=metrics["ndcg"],
                precision_at_k=metrics["precision_at_k"],
                keyword_coverage=metrics["keyword_coverage"],
                accuracy=metrics["accuracy"],
                failures=metrics["failures"],
                duration_ms=metrics["duration_ms"],
                parameters=metrics["parameters"],
            )
            row["id"] = int(saved.get("id") or 0)
            row["created_at"] = saved.get("created_at") or row["created_at"]
        except Exception as exc:
            await safe_rollback(db)
            raise HTTPException(
                status_code=500,
                detail=f"No se pudo guardar la comparación de estrategias: {exc}",
            ) from exc
        runs.append(_history_item_from_experiment(row))
    best = max(runs, key=lambda item: item.mrr) if runs else None
    return ExperimentCompareResponse(
        runs=runs,
        best_mrr_id=best.id if best else None,
        note=(
            "Ablación sobre el mismo banco, embedding, distancia y top-k. "
            "HyDE permanece como estrategia futura hasta disponer de implementación."
        ),
    )


@router.get("/conversations")
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await build_chat_container(db).conversations.list_for_user(current_user.id)


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await build_chat_container(db).conversations.get_with_messages(
            conversation_id, current_user.id
        )
    except AppError as exc:
        raise http_error(exc) from exc


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await build_chat_container(db).conversations.delete(
            conversation_id, current_user.id
        )
    except AppError as exc:
        raise http_error(exc) from exc


@lab_router.get("/evaluation/runtime-config")
async def get_evaluation_runtime_config(
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    return rag_runtime_config()


@lab_router.get("/evaluation/tests")
async def get_evaluation_tests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    organization_id: UUID | None = None,
):
    tests = await resolve_evaluation_tests(current_user, db, organization_id)
    return {
        "total": len(tests),
        "tests": [_serialize_test(idx, test) for idx, test in enumerate(tests)],
    }


@lab_router.get("/evaluation/tests/{test_id}")
async def get_evaluation_test(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    organization_id: UUID | None = None,
):
    tests = await resolve_evaluation_tests(current_user, db, organization_id)
    if test_id < 0 or test_id >= len(tests):
        raise HTTPException(status_code=404, detail="Test no encontrado")

    return _serialize_test(test_id, tests[test_id])


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        conv = build_chat_container(db).conversations
        org_id = getattr(request, "organization_id", None) or None
        member_info = await conv.resolve_tenant(current_user.id, org_id)

        tenant_id = member_info["tenant_id"]
        conversation_id = request.conversation_id
        kb_id = request.knowledge_base_id

        # Extracción del modelo de lenguaje gratuito seleccionado en el frontend (Ollama)
        selected_model = getattr(request, "model", None) or "llama3.2:latest"

        if kb_id == "undefined" or kb_id == "":
            kb_id = None
        collections = None

        conversation_id = await conv.ensure_conversation(
            conversation_id, tenant_id, current_user.id, kb_id, request.question
        )
        await conv.insert_message(conversation_id, "user", request.question)
        await conv.commit()

        org_name = request.organization_name or "AgroPS"
        comparison_payload = None
        agent_trace = None
        architecture = None
        rag_mode_used = "none"
        core_rag = RAGService(
            model=selected_model,
            retrieval_k=request.retrieval_k,
            bm25_k=max(10, request.retrieval_k),
            candidate_k=max(15, request.retrieval_k * 2),
            final_k=request.final_k,
        )

        if not request.use_rag:
            rag_result = await core_rag.simple_chat(
                request.question,
                history=request.history,
                temperature=request.temperature,
            )
            rag_result["retrieval_details"] = None
            architecture = "no_rag"
            rag_mode_used = "none"
        else:
            agentic = AgenticRAGService(rag=core_rag)
            mode = request.rag_mode or "agentic"
            hybrid_kwargs = {
                "question": request.question,
                "tenant_id": str(tenant_id),
                "collections": collections,
                "model": selected_model,
                "history": request.history,
                "use_reranking": request.use_reranking,
                "use_query_rewrite": request.use_query_rewrite,
                "temperature": request.temperature,
            }
            if mode == "hybrid":
                rag_result = await run_hybrid_answer(core_rag, **hybrid_kwargs)
                rag_mode_used = "hybrid"
            elif mode == "compare":
                hybrid_result = await run_hybrid_answer(core_rag, **hybrid_kwargs)
                agentic_result = await agentic.answer(
                    request.question,
                    tenant_id=str(tenant_id),
                    collections=collections,
                    model=selected_model,
                    history=request.history,
                    organization_name=org_name,
                    conversation_id=str(conversation_id) if conversation_id else None,
                    user_id=str(current_user.id),
                    organization_id=str(org_id) if org_id else None,
                    use_reranking=request.use_reranking,
                    use_query_rewrite=request.use_query_rewrite,
                    temperature=request.temperature,
                )
                comparison_payload = {
                    "hybrid": pack_mode_side(hybrid_result, "hybrid"),
                    "agentic": pack_mode_side(agentic_result, "agentic"),
                    "note": (
                        "Mismo corpus y misma pregunta. Hybrid recorre el pipeline "
                        "fijo denso+BM25+RRF. Agentic usa LangGraph: el LLM "
                        "decide si recuperar, puntúa la relevancia y puede "
                        "reescribir la pregunta; también puede usar SQL y memoria."
                    ),
                }
                rag_result = agentic_result
                rag_mode_used = "compare"
            else:
                rag_result = await agentic.answer(
                    request.question,
                    tenant_id=str(tenant_id),
                    collections=collections,
                    model=selected_model,
                    history=request.history,
                    organization_name=org_name,
                    conversation_id=str(conversation_id) if conversation_id else None,
                    user_id=str(current_user.id),
                    organization_id=str(org_id) if org_id else None,
                    use_reranking=request.use_reranking,
                    use_query_rewrite=request.use_query_rewrite,
                    temperature=request.temperature,
                )
                rag_mode_used = "agentic"
            architecture = rag_result.get("architecture")
            agent_trace = rag_result.get("agent_trace")

        answer = rag_result["answer"]
        chunks = rag_result["chunks"]
        retrieval = rag_result["retrieval"]

        assistant_message_id = await conv.insert_message(
            conversation_id, "assistant", answer
        )
        for chunk in chunks:
            metadata = getattr(chunk, "metadata", None)
            if metadata is None and isinstance(chunk, dict):
                metadata = chunk.get("metadata", {})
            metadata = metadata or {}
            await conv.insert_source(
                assistant_message_id,
                metadata.get("document_id"),
                metadata.get("chunk_id"),
                metadata.get("score"),
            )
        await conv.touch(conversation_id)
        await conv.commit()

        review_id = None
        try:
            await init_human_validation_tables(db)
            review_id = await queue_chat_review(
                db,
                user_id=str(current_user.id),
                organization_id=str(request.organization_id)
                if request.organization_id
                else None,
                conversation_id=str(conversation_id) if conversation_id else None,
                question=request.question,
                answer=answer,
                chunks=chunks,
            )
        except Exception:
            review_id = None

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
            rag_mode=rag_mode_used,
            architecture=architecture,
            agent_trace=agent_trace,
            comparison=comparison_payload,
            review_id=review_id,
        )

    except AppError as exc:
        await db.rollback()
        raise http_error(exc) from exc
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        err = str(e)
        if "not found" in err.lower() and "model" in err.lower():
            raise HTTPException(
                status_code=503,
                detail=(
                    "Ollama no tiene el modelo de embeddings o de generación. "
                    "Descárgalos con: docker compose exec ollama ollama pull "
                    "nomic-embed-text && docker compose exec ollama "
                    "ollama pull llama3.2:latest"
                ),
            ) from e
        if any(
            token in err.lower()
            for token in ("vector", "sqlalchemy", "asyncpg", "psycopg", "[sql:")
        ):
            raise HTTPException(
                status_code=503,
                detail=(
                    "No se pudo buscar en el corpus. Los documentos siguen en "
                    "PostgreSQL; el embedding de consulta no coincidía con el índice."
                ),
            ) from e
        raise HTTPException(status_code=500, detail="No se pudo completar la consulta.")


@lab_router.post("/evaluation/retrieval/{test_id}")
async def evaluate_retrieval_route(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    organization_id: UUID | None = None,
    knowledge_base_id: UUID | None = None,
    distance_metric: str = "cosine",
    embedding_model: str | None = None,
    top_k: int = EVAL_TOP_K,
):
    tests = await resolve_evaluation_tests(
        current_user, db, organization_id
    )
    if test_id < 0 or test_id >= len(tests):
        raise HTTPException(status_code=404, detail="Test no encontrado")

    tenant_id = await get_user_tenant_id(
        current_user.id, db, organization_id=organization_id
    )
    test = tests[test_id]
    collections = [str(knowledge_base_id)] if knowledge_base_id else None

    result = await evaluate_retrieval_internal(
        test,
        str(tenant_id),
        k=max(1, top_k),
        collections=collections,
        distance_metric=_normalize_distance_metric(distance_metric),
        embedding_model=embedding_model or DEFAULT_EMBEDDING_MODEL,
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


@lab_router.post("/evaluation/answer/{test_id}")
async def evaluate_answer_route(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    organization_id: UUID | None = None,
    knowledge_base_id: UUID | None = None,
    temperature: float | None = None,
    top_k: int = EVAL_TOP_K,
):
    tests = await resolve_evaluation_tests(
        current_user, db, organization_id
    )
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
    eval_result, generated_answer, chunks, retrieval = await evaluate_answer_internal(
        test,
        str(tenant_id),
        collections=collections,
        temperature=temperature,
        k=max(1, top_k),
    )

    eval_data = (
        eval_result.model_dump() if hasattr(eval_result, "model_dump") else eval_result
    )
    retrieval_data = (
        retrieval.model_dump() if hasattr(retrieval, "model_dump") else retrieval
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
        "retrieval": retrieval_data,
        "retrieved_chunks": [
            {
                "content": getattr(chunk, "page_content", str(chunk)),
                "metadata": getattr(chunk, "metadata", {}),
            }
            for chunk in chunks
        ],
    }


@lab_router.post("/evaluation/upload-tests")
async def upload_tests(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    organization_id: UUID | None = None,
    replace_dataset: bool = False,
):
    """Sube JSON/JSONL del banco: guarda el fichero y lo inserta en retrieval_dataset.

    - ``organization_id`` acota el tenant de la organización activa.
    - ``replace_dataset``: si es true, vacía las filas del tenant con origen
      file/json_upload antes de insertar (no borra HITL anotado).
    """
    tenant_id = await get_user_tenant_id(
        current_user.id, db, organization_id=organization_id
    )

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except Exception:
        text = content.decode("latin-1")

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            lines = [json.dumps(item, ensure_ascii=False) for item in parsed]
        else:
            lines = [json.dumps(parsed, ensure_ascii=False)]
    except Exception:
        lines = [line for line in text.splitlines() if line.strip()]

    canonical_rows: list[dict] = []
    seen_questions: set[str] = set()
    for line in lines:
        try:
            row = json.loads(line)
            item = TestQuestion(**row)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Dataset inválido: {exc}")
        key = " ".join(item.question.casefold().split())
        if not key or key in seen_questions:
            continue
        seen_questions.add(key)
        payload = item.model_dump()
        meta = dict(payload.get("metadata") or {})
        meta.setdefault("source", "json_upload")
        if organization_id:
            meta["organization_id"] = str(organization_id)
        payload["metadata"] = meta
        canonical_rows.append(payload)

    if not canonical_rows:
        raise HTTPException(
            status_code=400,
            detail="El fichero no contiene preguntas válidas.",
        )

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

    imported = 0
    updated = 0
    try:
        await init_retrieval_dataset_table(db)
        if replace_dataset:
            await db.execute(
                text("""
                    DELETE FROM public.retrieval_dataset
                    WHERE tenant_id = :tenant_id
                      AND COALESCE(metadata->>'source', 'file') IN (
                          'file', 'json_upload', 'merged'
                      )
                """),
                {"tenant_id": tenant_id},
            )
        for item in [TestQuestion(**row) for row in canonical_rows]:
            question = item.question.strip()
            meta = dict(item.metadata or {})
            meta.setdefault("source", "json_upload")
            params = {
                "tenant_id": tenant_id,
                "question": question,
                "expected_chunk_id": "",
                "selected_chunk_ids": json.dumps([]),
                "keywords": json.dumps(list(item.keywords or [])),
                "reference_answer": item.reference_answer or None,
                "category": item.category or "general",
                "out_of_knowledge": bool(item.out_of_knowledge),
                "split": item.split or "dev",
                "metadata": json.dumps(meta, ensure_ascii=False),
            }
            existing = await db.execute(
                text("""
                    SELECT id
                    FROM public.retrieval_dataset
                    WHERE tenant_id = :tenant_id
                      AND lower(btrim(question)) = lower(btrim(:question))
                    LIMIT 1
                """),
                {"tenant_id": tenant_id, "question": question},
            )
            row_id = existing.scalar_one_or_none()
            if row_id is not None:
                await db.execute(
                    text("""
                        UPDATE public.retrieval_dataset
                        SET keywords = CAST(:keywords AS JSONB),
                            reference_answer = :reference_answer,
                            category = :category,
                            flag_out_of_knowledge = :out_of_knowledge,
                            split = :split,
                            metadata = COALESCE(metadata, '{}'::jsonb)
                                || CAST(:metadata AS JSONB)
                        WHERE id = :id
                    """),
                    {**params, "id": row_id},
                )
                updated += 1
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
                        :expected_chunk_id,
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
                params,
            )
            imported += 1
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo insertar el banco en retrieval_dataset: {exc}",
        ) from exc

    return {
        "status": "ok",
        "uploaded": len(canonical_rows),
        "imported": imported,
        "updated": updated,
        "skipped": 0,
        "tenant_id": tenant_id,
        "path": tests_path,
    }


@lab_router.post("/simulator/save-dataset")
async def save_to_dataset(
    request: SimulatorSaveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    organization_id: UUID | None = None,
):
    tenant_id = await get_user_tenant_id(
        current_user.id,
        db,
        organization_id=organization_id,
    )

    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="La pregunta no puede estar vacía.",
        )

    if (
        not request.flags.out_of_knowledge
        and not request.flags.different_info
        and not request.selected_chunk_ids
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Selecciona el fragmento correcto, indica otra respuesta "
                "o marca la pregunta como fuera de la base de conocimiento."
            ),
        )

    try:
        await init_retrieval_dataset_table(db)

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
                "expected_chunk_id": _expected_chunk_sql(
                    request.selected_chunk_ids[0]
                    if request.selected_chunk_ids
                    else None
                ),
                "selected_chunk_ids": json.dumps(request.selected_chunk_ids),
                "keywords": json.dumps(request.keywords or []),
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


@lab_router.post("/simulator/search")
async def simulator_search(
    request: SimulatorSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    organization_id: UUID | None = None,
):
    tenant_id = await get_user_tenant_id(
        current_user.id,
        db,
        organization_id=organization_id,
    )

    rag_result = await rag_service.fetch_context(
        question=request.question,
        tenant_id=str(tenant_id),
        collections=[request.knowledge_base_id] if request.knowledge_base_id else None,
        evaluation_mode=request.evaluation_mode,
        distance_metric=request.distance_metric,
        retrieval_strategy="dense",
    )

    chunks = rag_result.get("chunks", []) or []

    results = []

    for rank, chunk in enumerate(chunks, start=1):
        metadata = getattr(chunk, "metadata", None)
        if metadata is None and isinstance(chunk, dict):
            metadata = chunk.get("metadata") or {}
        metadata = metadata or {}
        page_content = getattr(chunk, "page_content", None)
        if page_content is None and isinstance(chunk, dict):
            page_content = chunk.get("page_content") or ""
        page_content = str(page_content or "")
        snippet = " ".join(page_content.split())
        headline = str(metadata.get("headline") or "").strip()
        source = str(metadata.get("source") or "").strip()
        title = headline or source or snippet or f"Fragmento #{rank}"
        if len(title) > 96:
            title = title[:93].rstrip() + "…"
        distance = metadata.get("distance")
        try:
            distance = float(distance) if distance is not None else None
        except (TypeError, ValueError):
            distance = None

        results.append(
            {
                "id": str(metadata.get("chunk_id") or ""),
                "rank": rank,
                "title": title,
                "description": page_content[:1000],
                "score": metadata.get(
                    "cross_encoder_score",
                    metadata.get("rrf_score", 0.0),
                ),
                "distance": distance,
                "content": page_content,
            }
        )

    return {
        "question": request.question,
        "distance_metric": request.distance_metric,
        "chunks": results,
        "retrieval": rag_result.get("retrieval", {}),
    }


@lab_router.post("/retrieve")
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


@lab_router.get("/evaluation/stream-run")
async def stream_evaluation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await get_user_tenant_id(current_user.id, db)
    tests = await load_unified_tests(db, tenant_id, validated_only=True)

    async def event_generator():
        answer_results = []

        for idx, test in enumerate(tests):
            # Llamada directa usando await
            eval_result, generated_answer, _, retrieval = await evaluate_answer_internal(
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
                    "mrr": getattr(eval_result, "mrr", 0.0),
                    "ndcg": getattr(eval_result, "ndcg", 0.0),
                    "keyword_coverage": getattr(eval_result, "keyword_coverage", 0.0),
                    "retrieval_mrr": getattr(retrieval, "mrr", 0.0),
                    "retrieval_ndcg": getattr(retrieval, "ndcg", 0.0),
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
