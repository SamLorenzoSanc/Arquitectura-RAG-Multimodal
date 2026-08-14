"""Esquema de retrieval_dataset en Postgres remoto (Render no corre migraciones locales)."""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

CREATE_RETRIEVAL_DATASET_SQL = """
CREATE TABLE IF NOT EXISTS public.retrieval_dataset (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    question TEXT NOT NULL,
    expected_chunk_id TEXT,
    selected_chunk_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    reference_answer TEXT,
    category TEXT NOT NULL DEFAULT 'general',
    flag_different_info BOOLEAN NOT NULL DEFAULT FALSE,
    flag_out_of_knowledge BOOLEAN NOT NULL DEFAULT FALSE,
    split TEXT NOT NULL DEFAULT 'dev',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
)
"""

_ADD_COLUMNS_SQL = (
    "ALTER TABLE public.retrieval_dataset ADD COLUMN IF NOT EXISTS selected_chunk_ids JSONB NOT NULL DEFAULT '[]'::jsonb",
    "ALTER TABLE public.retrieval_dataset ADD COLUMN IF NOT EXISTS keywords JSONB NOT NULL DEFAULT '[]'::jsonb",
    "ALTER TABLE public.retrieval_dataset ADD COLUMN IF NOT EXISTS reference_answer TEXT",
    "ALTER TABLE public.retrieval_dataset ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'general'",
    "ALTER TABLE public.retrieval_dataset ADD COLUMN IF NOT EXISTS flag_different_info BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE public.retrieval_dataset ADD COLUMN IF NOT EXISTS flag_out_of_knowledge BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE public.retrieval_dataset ADD COLUMN IF NOT EXISTS split TEXT NOT NULL DEFAULT 'dev'",
    "ALTER TABLE public.retrieval_dataset ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb",
    "ALTER TABLE public.retrieval_dataset ADD COLUMN IF NOT EXISTS expected_chunk_id TEXT",
)


async def safe_rollback(db: AsyncSession | None) -> None:
    if db is None:
        return
    try:
        await db.rollback()
    except Exception:
        pass


async def init_retrieval_dataset_table(db: AsyncSession) -> None:
    await db.execute(text(CREATE_RETRIEVAL_DATASET_SQL))
    for statement in _ADD_COLUMNS_SQL:
        await db.execute(text(statement))
    await db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_retrieval_dataset_tenant_question_normalized
            ON public.retrieval_dataset (tenant_id, lower(btrim(question)))
            """
        )
    )
    await db.commit()


CREATE_EXPERIMENT_RUNS_SQL = """
CREATE TABLE IF NOT EXISTS public.rag_experiment_runs (
    id SERIAL PRIMARY KEY,
    tenant_id UUID,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    embedding_model TEXT NOT NULL,
    distance_metric TEXT NOT NULL,
    generation_model TEXT,
    experiment_type TEXT NOT NULL DEFAULT 'question_bank',
    dataset_size INTEGER NOT NULL DEFAULT 0,
    evaluated_questions INTEGER NOT NULL DEFAULT 0,
    recall_1 DOUBLE PRECISION,
    recall_k DOUBLE PRECISION,
    mrr DOUBLE PRECISION,
    ndcg DOUBLE PRECISION,
    precision_at_k DOUBLE PRECISION,
    keyword_coverage DOUBLE PRECISION,
    accuracy DOUBLE PRECISION,
    failures INTEGER NOT NULL DEFAULT 0,
    duration_ms DOUBLE PRECISION,
    status TEXT NOT NULL DEFAULT 'completed',
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb
)
"""


async def init_experiment_runs_table(db: AsyncSession) -> None:
    await db.execute(text(CREATE_EXPERIMENT_RUNS_SQL))
    await db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_rag_experiment_runs_tenant_created
            ON public.rag_experiment_runs (tenant_id, created_at DESC)
            """
        )
    )
    await db.commit()


INSERT_EXPERIMENT_RUN_SQL = """
INSERT INTO public.rag_experiment_runs (
    tenant_id,
    embedding_model,
    distance_metric,
    generation_model,
    experiment_type,
    dataset_size,
    evaluated_questions,
    recall_1,
    recall_k,
    mrr,
    ndcg,
    precision_at_k,
    keyword_coverage,
    accuracy,
    failures,
    duration_ms,
    status,
    parameters
)
VALUES (
    :tenant_id,
    :embedding_model,
    :distance_metric,
    :generation_model,
    :experiment_type,
    :dataset_size,
    :evaluated_questions,
    :recall_1,
    :recall_k,
    :mrr,
    :ndcg,
    :precision_at_k,
    :keyword_coverage,
    :accuracy,
    :failures,
    :duration_ms,
    :status,
    CAST(:parameters AS JSONB)
)
RETURNING id, created_at
"""


async def record_experiment_run(
    db: AsyncSession,
    *,
    tenant_id: str,
    embedding_model: str,
    distance_metric: str,
    generation_model: str | None = None,
    experiment_type: str = "question_bank",
    dataset_size: int = 0,
    evaluated_questions: int = 0,
    recall_1: float | None = None,
    recall_k: float | None = None,
    mrr: float | None = None,
    ndcg: float | None = None,
    precision_at_k: float | None = None,
    keyword_coverage: float | None = None,
    accuracy: float | None = None,
    failures: int = 0,
    duration_ms: float | None = None,
    status: str = "completed",
    parameters: dict | None = None,
) -> dict:
    """Persiste una corrida comparable (embedding × distancia × métricas)."""
    await init_experiment_runs_table(db)
    result = await db.execute(
        text(INSERT_EXPERIMENT_RUN_SQL),
        {
            "tenant_id": tenant_id,
            "embedding_model": embedding_model,
            "distance_metric": distance_metric,
            "generation_model": generation_model,
            "experiment_type": experiment_type,
            "dataset_size": dataset_size,
            "evaluated_questions": evaluated_questions,
            "recall_1": recall_1,
            "recall_k": recall_k,
            "mrr": mrr,
            "ndcg": ndcg,
            "precision_at_k": precision_at_k,
            "keyword_coverage": keyword_coverage,
            "accuracy": accuracy,
            "failures": failures,
            "duration_ms": duration_ms,
            "status": status,
            "parameters": json.dumps(parameters or {}),
        },
    )
    row = result.mappings().first()
    await db.commit()
    return dict(row) if row else {}


async def insert_extracted_questions_into_bank(
    db: AsyncSession,
    *,
    tenant_id: str,
    questions: list[dict],
    document_id: str | None = None,
) -> int:
    """Copia preguntas extraídas del PDF al banco de evaluación (sin duplicar)."""
    await init_retrieval_dataset_table(db)
    imported = 0
    for item in questions:
        question = (item.get("question") or "").strip()
        if not question:
            continue
        existing = await db.execute(
            text(
                """
                SELECT id FROM public.retrieval_dataset
                WHERE tenant_id = :tenant_id
                  AND lower(btrim(question)) = lower(btrim(:question))
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "question": question},
        )
        if existing.scalar_one_or_none() is not None:
            continue
        keywords = item.get("keywords") or []
        if not isinstance(keywords, list):
            keywords = []
        metadata = {"source": "hitl", "document_id": document_id}
        await db.execute(
            text(
                """
                INSERT INTO public.retrieval_dataset (
                    tenant_id, question, expected_chunk_id, selected_chunk_ids,
                    keywords, reference_answer, category, flag_different_info,
                    flag_out_of_knowledge, split, metadata
                ) VALUES (
                    :tenant_id, :question, NULL, '[]'::jsonb,
                    CAST(:keywords AS JSONB), :reference_answer, :category,
                    FALSE, :out_of_knowledge, 'dev', CAST(:metadata AS JSONB)
                )
                """
            ),
            {
                "tenant_id": tenant_id,
                "question": question,
                "keywords": json.dumps(keywords, ensure_ascii=False),
                "reference_answer": (item.get("reference_answer") or item.get("rationale") or "")
                or None,
                "category": (item.get("category") or "general"),
                "out_of_knowledge": bool(item.get("out_of_knowledge")),
                "metadata": json.dumps(metadata, ensure_ascii=False),
            },
        )
        imported += 1
    await db.commit()
    return imported
