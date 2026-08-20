"""Cola HITL: validación humana de respuestas RAG y preguntas extraídas."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_KEYWORD_STOPWORDS = frozenset(
    """
    el la los las un una unos unas de del al a y o en que se por con para
    es son del no si sí como cómo cual cuál qué quien quién donde dónde
    este esta esto hay tiene tienen debe deben según
    """.split()
)


def coerce_keywords(value: Any, *texts: str) -> list[str]:
    items: list[str] = []
    parsed = value
    if isinstance(parsed, str):
        stripped = parsed.strip()
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                parsed = [part.strip() for part in stripped.split(",") if part.strip()]
        else:
            parsed = [part.strip() for part in stripped.split(",") if part.strip()]
    if isinstance(parsed, list):
        items = [str(item).strip() for item in parsed if str(item).strip()]
    if items:
        return items[:8]
    blob = " ".join(str(part) for part in texts if part)
    for token in re.findall(
        r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9.,%]{2,}",
        blob,
    ):
        clean = token.strip(".,")
        if not clean or clean.casefold() in _KEYWORD_STOPWORDS:
            continue
        if clean not in items:
            items.append(clean)
        if len(items) >= 8:
            break
    return items

CREATE_QUESTIONS_SQL = """
CREATE TABLE IF NOT EXISTS document_questions (
    id VARCHAR(36) PRIMARY KEY,
    document_id UUID,
    knowledge_base_id UUID,
    organization_id UUID,
    user_id VARCHAR(36),
    question TEXT NOT NULL,
    rationale TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP WITHOUT TIME ZONE,
    reviewer_notes TEXT
)
"""

_ADD_QUESTION_COLUMNS_SQL = (
    "ALTER TABLE document_questions ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'general'",
    "ALTER TABLE document_questions ADD COLUMN IF NOT EXISTS keywords JSONB NOT NULL DEFAULT '[]'::jsonb",
    "ALTER TABLE document_questions ADD COLUMN IF NOT EXISTS reference_answer TEXT",
    "ALTER TABLE document_questions ADD COLUMN IF NOT EXISTS filename TEXT",
)

_ADD_REVIEW_COLUMNS_SQL = (
    "ALTER TABLE rag_human_reviews ADD COLUMN IF NOT EXISTS category TEXT",
    "ALTER TABLE rag_human_reviews ADD COLUMN IF NOT EXISTS filename TEXT",
    "ALTER TABLE rag_human_reviews ADD COLUMN IF NOT EXISTS knowledge_base_id UUID",
    "ALTER TABLE rag_human_reviews ADD COLUMN IF NOT EXISTS rationale TEXT",
    "ALTER TABLE rag_human_reviews ADD COLUMN IF NOT EXISTS keywords JSONB NOT NULL DEFAULT '[]'::jsonb",
)

CREATE_REVIEWS_SQL = """
CREATE TABLE IF NOT EXISTS rag_human_reviews (
    id VARCHAR(36) PRIMARY KEY,
    source VARCHAR(40) NOT NULL DEFAULT 'chat',
    user_id VARCHAR(36),
    organization_id UUID,
    conversation_id VARCHAR(36),
    document_id UUID,
    question TEXT NOT NULL,
    answer TEXT,
    context_snippet TEXT,
    chunk_ids JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    corrected_answer TEXT,
    reviewer_notes TEXT,
    reviewer_id VARCHAR(36),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP WITHOUT TIME ZONE
)
"""


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for key in (
        "id",
        "document_id",
        "knowledge_base_id",
        "organization_id",
        "user_id",
        "conversation_id",
        "reviewer_id",
    ):
        if out.get(key) is not None:
            out[key] = str(out[key])
    for key in ("created_at", "reviewed_at"):
        value = out.get(key)
        if isinstance(value, datetime):
            out[key] = value.isoformat()
    if out.get("chunk_ids") is not None and not isinstance(out["chunk_ids"], list):
        out["chunk_ids"] = list(out["chunk_ids"]) if out["chunk_ids"] else []
    if isinstance(out.get("keywords"), str):
        try:
            parsed = json.loads(out["keywords"])
            out["keywords"] = parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            out["keywords"] = []
    return out


async def init_human_validation_tables(db: AsyncSession) -> None:
    await db.execute(text(CREATE_QUESTIONS_SQL))
    await db.execute(text(CREATE_REVIEWS_SQL))
    for statement in _ADD_QUESTION_COLUMNS_SQL:
        await db.execute(text(statement))
    for statement in _ADD_REVIEW_COLUMNS_SQL:
        await db.execute(text(statement))
    await db.commit()


async def save_document_questions(
    db: AsyncSession,
    *,
    document_id: str,
    knowledge_base_id: str | None,
    organization_id: str | None,
    user_id: str | None,
    questions: list[dict[str, str]],
    filename: str | None = None,
) -> list[dict[str, Any]]:
    stored: list[dict[str, Any]] = []
    for item in questions:
        question = (item.get("question") or "").strip()
        if not question:
            continue
        qid = str(uuid4())
        rationale = (item.get("rationale") or "").strip() or None
        category = (item.get("category") or "general").strip() or "general"
        reference_answer = (item.get("reference_answer") or "").strip() or None
        keywords = coerce_keywords(
            item.get("keywords") or [], question, reference_answer or ""
        )
        await db.execute(
            text(
                """
                INSERT INTO document_questions (
                    id, document_id, knowledge_base_id, organization_id,
                    user_id, question, rationale, status, category,
                    keywords, reference_answer, filename
                ) VALUES (
                    :id, :document_id, :knowledge_base_id, :organization_id,
                    :user_id, :question, :rationale, 'pending', :category,
                    CAST(:keywords AS jsonb), :reference_answer, :filename
                )
                """
            ),
            {
                "id": qid,
                "document_id": document_id,
                "knowledge_base_id": knowledge_base_id,
                "organization_id": organization_id,
                "user_id": user_id,
                "question": question,
                "rationale": rationale,
                "category": category,
                "keywords": json.dumps(keywords, ensure_ascii=False),
                "reference_answer": reference_answer,
                "filename": filename,
            },
        )
        rid = str(uuid4())
        await db.execute(
            text(
                """
                INSERT INTO rag_human_reviews (
                    id, source, user_id, organization_id, document_id,
                    knowledge_base_id, question, answer, context_snippet,
                    status, category, filename, rationale, keywords
                ) VALUES (
                    :id, 'document_question', :user_id, :organization_id,
                    :document_id, :knowledge_base_id, :question, :answer,
                    :context_snippet, 'pending', :category, :filename, :rationale,
                    CAST(:keywords AS jsonb)
                )
                """
            ),
            {
                "id": rid,
                "user_id": user_id,
                "organization_id": organization_id,
                "document_id": document_id,
                "knowledge_base_id": knowledge_base_id,
                "question": question,
                "answer": reference_answer,
                "context_snippet": rationale,
                "category": category,
                "filename": filename,
                "rationale": rationale,
                "keywords": json.dumps(keywords, ensure_ascii=False),
            },
        )
        stored.append(
            {
                "id": qid,
                "review_id": rid,
                "question": question,
                "rationale": rationale,
                "category": category,
                "keywords": keywords,
                "reference_answer": reference_answer,
                "filename": filename,
                "status": "pending",
            }
        )
    await db.commit()
    return stored


async def enqueue_document_eval_questions(
    db: AsyncSession | None = None,
    *,
    document_id: str,
) -> int:
    """Extrae preguntas del documento indexado y las deja pendientes de HITL.

    Usa una sesión propia para no dejar la conexión de ingesta bloqueada
    mientras el LLM genera las preguntas.
    """
    import asyncio

    from services.database import AsyncSessionLocal
    from services.question_extraction import (
        extract_questions_with_llm,
        heuristic_questions,
    )

    async def _load() -> tuple[dict[str, Any] | None, str]:
        session = db
        owns = session is None
        if owns:
            session = AsyncSessionLocal()
        assert session is not None
        try:
            await init_human_validation_tables(session)
            document = (
                await session.execute(
                    text(
                        """
                        SELECT
                            d.filename,
                            d.owner_id,
                            d.tenant_id,
                            d.knowledge_base_id,
                            t.organization_id
                        FROM public.documents d
                        JOIN public.tenants t ON t.id = d.tenant_id
                        WHERE d.id = :document_id
                        LIMIT 1
                        """
                    ),
                    {"document_id": document_id},
                )
            ).mappings().first()
            if not document:
                return None, ""
            chunk_rows = (
                await session.execute(
                    text(
                        """
                        SELECT headline, summary, content
                        FROM public.chunks
                        WHERE document_id = :document_id
                        ORDER BY position ASC
                        LIMIT 40
                        """
                    ),
                    {"document_id": document_id},
                )
            ).mappings().all()
            parts: list[str] = []
            for row in chunk_rows:
                for key in ("headline", "summary", "content"):
                    value = str(row.get(key) or "").strip()
                    if value:
                        parts.append(value)
            await session.commit()
            return dict(document), "\n\n".join(parts)
        finally:
            if owns:
                await session.close()

    document, blob = await _load()
    if not document:
        return 0
    if not blob.strip():
        logger.info("Sin texto indexado para extraer preguntas de %s", document_id)
        return 0

    filename = document.get("filename") or "documento"
    timeout = float(os.getenv("RAG_EVAL_QUESTION_TIMEOUT", "25"))
    try:
        questions = await asyncio.wait_for(
            asyncio.to_thread(extract_questions_with_llm, blob, filename),
            timeout=timeout,
        )
    except Exception:
        logger.exception("LLM no extrajo preguntas de %s; se usa heurística", document_id)
        questions = heuristic_questions(blob, filename)
    if not questions:
        questions = heuristic_questions(blob, filename)
    if not questions:
        return 0

    async with AsyncSessionLocal() as session:
        await init_human_validation_tables(session)
        await session.execute(
            text(
                """
                DELETE FROM rag_human_reviews
                WHERE document_id = :document_id
                  AND source = 'document_question'
                  AND status = 'pending'
                """
            ),
            {"document_id": document_id},
        )
        await session.execute(
            text(
                """
                DELETE FROM document_questions
                WHERE document_id = :document_id
                  AND status = 'pending'
                """
            ),
            {"document_id": document_id},
        )
        await session.commit()
        stored = await save_document_questions(
            session,
            document_id=document_id,
            knowledge_base_id=(
                str(document["knowledge_base_id"])
                if document.get("knowledge_base_id")
                else None
            ),
            organization_id=(
                str(document["organization_id"])
                if document.get("organization_id")
                else None
            ),
            user_id=str(document["owner_id"]) if document.get("owner_id") else None,
            questions=questions,
            filename=filename,
        )
        tenant_id = document.get("tenant_id")
        if tenant_id and stored:
            from services.evaluation_dataset import insert_extracted_questions_into_bank

            try:
                await insert_extracted_questions_into_bank(
                    session,
                    tenant_id=str(tenant_id),
                    questions=questions,
                    document_id=document_id,
                    validated=False,
                )
            except Exception:
                logger.exception(
                    "No se pudieron guardar en el banco las preguntas de %s",
                    document_id,
                )
    logger.info(
        "Encoladas %s preguntas HITL para %s (%s)",
        len(stored),
        filename,
        document_id,
    )
    return len(stored)


async def enqueue_missing_document_eval_questions(
    *,
    organization_id: str | None = None,
    limit: int = 8,
) -> dict[str, int]:
    """Genera preguntas HITL para documentos indexados que aún no tienen cola."""
    from services.database import AsyncSessionLocal

    clauses = [
        "EXISTS (SELECT 1 FROM public.chunks c WHERE c.document_id = d.id)",
        """
        NOT EXISTS (
            SELECT 1 FROM rag_human_reviews r
            WHERE r.document_id = d.id
              AND r.source = 'document_question'
        )
        """,
    ]
    params: dict[str, Any] = {"limit": max(1, min(int(limit), 20))}
    if organization_id:
        clauses.append("t.organization_id = :organization_id")
        params["organization_id"] = organization_id
    async with AsyncSessionLocal() as session:
        await init_human_validation_tables(session)
        rows = (
            await session.execute(
                text(
                    f"""
                    SELECT d.id
                    FROM public.documents d
                    JOIN public.tenants t ON t.id = d.tenant_id
                    WHERE {' AND '.join(clauses)}
                    ORDER BY d.uploaded_at DESC NULLS LAST
                    LIMIT :limit
                    """
                ),
                params,
            )
        ).all()
        ids = [str(row[0]) for row in rows]
    queued_docs = 0
    queued_questions = 0
    for doc_id in ids:
        try:
            count = await enqueue_document_eval_questions(document_id=doc_id)
        except Exception:
            logger.exception("No se pudieron extraer preguntas de %s", doc_id)
            continue
        if count:
            queued_docs += 1
            queued_questions += count
    return {
        "scanned": len(ids),
        "documents": queued_docs,
        "questions": queued_questions,
    }


async def _resolve_tenant_id(
    db: AsyncSession,
    *,
    document_id: str | None,
    organization_id: str | None,
) -> str | None:
    if document_id:
        doc = await db.execute(
            text("SELECT tenant_id FROM public.documents WHERE id = :id LIMIT 1"),
            {"id": document_id},
        )
        row = doc.mappings().first()
        if row and row.get("tenant_id"):
            return str(row["tenant_id"])
    if organization_id:
        tenant = await db.execute(
            text(
                """
                SELECT id FROM public.tenants
                WHERE organization_id = :organization_id
                LIMIT 1
                """
            ),
            {"organization_id": organization_id},
        )
        row = tenant.mappings().first()
        if row and row.get("id"):
            return str(row["id"])
    return None


async def promote_review_to_evaluation_bank(
    db: AsyncSession,
    *,
    document_id: str | None,
    question: str,
    reference_answer: str | None,
    category: str | None = None,
    keywords: list[str] | None = None,
    organization_id: str | None = None,
    filename: str | None = None,
) -> None:
    """Tras aprobar o corregir, entra en el JSONL del banco y en retrieval_dataset."""
    question = (question or "").strip()
    if not question:
        return
    from core.test import upsert_test_question_jsonl
    from services.evaluation_dataset import (
        insert_extracted_questions_into_bank,
        mark_hitl_question_in_bank,
    )

    meta: dict[str, Any] = {}
    if document_id:
        extra = await db.execute(
            text(
                """
                SELECT keywords, category, reference_answer, rationale
                FROM document_questions
                WHERE document_id = :document_id AND question = :question
                LIMIT 1
                """
            ),
            {"document_id": document_id, "question": question},
        )
        meta = dict(extra.mappings().first() or {})
    answer = (
        (reference_answer or "").strip()
        or str(meta.get("reference_answer") or "")
        or str(meta.get("rationale") or "")
    )
    cat = (category or meta.get("category") or "direct_fact").strip() or "direct_fact"
    keys = coerce_keywords(keywords if keywords is not None else meta.get("keywords"), question, answer)
    try:
        upsert_test_question_jsonl(
            question=question,
            keywords=keys,
            reference_answer=answer,
            category=cat,
            source_file=filename or "",
        )
    except Exception:
        logger.exception("No se pudo escribir la pregunta HITL en el JSONL del banco")

    tenant_id = await _resolve_tenant_id(
        db, document_id=document_id, organization_id=organization_id
    )
    if not tenant_id:
        return
    await insert_extracted_questions_into_bank(
        db,
        tenant_id=tenant_id,
        questions=[
            {
                "question": question,
                "keywords": keys,
                "reference_answer": answer,
                "category": cat,
                "out_of_knowledge": cat == "out_of_knowledge",
                "validated": True,
            }
        ],
        document_id=str(document_id) if document_id else None,
        validated=True,
    )
    await mark_hitl_question_in_bank(
        db,
        tenant_id=tenant_id,
        question=question,
        reference_answer=answer,
        category=cat,
        keywords=keys,
        validated=True,
    )


async def queue_chat_review(
    db: AsyncSession,
    *,
    user_id: str | None,
    organization_id: str | None,
    conversation_id: str | None,
    question: str,
    answer: str,
    chunks: list[Any] | None = None,
) -> str | None:
    review_id = str(uuid4())
    snippets: list[str] = []
    chunk_ids: list[str] = []
    for chunk in chunks or []:
        metadata = getattr(chunk, "metadata", None)
        content = getattr(chunk, "page_content", None)
        if metadata is None and isinstance(chunk, dict):
            metadata = chunk.get("metadata") or {}
            content = content or chunk.get("page_content")
        metadata = metadata or {}
        cid = metadata.get("chunk_id") or metadata.get("id")
        if cid:
            chunk_ids.append(str(cid))
        if content:
            snippets.append(str(content)[:280])

    await db.execute(
        text(
            """
            INSERT INTO rag_human_reviews (
                id, source, user_id, organization_id, conversation_id,
                question, answer, context_snippet, chunk_ids, status
            ) VALUES (
                :id, 'chat', :user_id, :organization_id, :conversation_id,
                :question, :answer, :context_snippet, CAST(:chunk_ids AS jsonb),
                'pending'
            )
            """
        ),
        {
            "id": review_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "conversation_id": conversation_id,
            "question": question,
            "answer": answer,
            "context_snippet": "\n---\n".join(snippets[:3]) or None,
            "chunk_ids": json.dumps(chunk_ids[:8]),
        },
    )
    await db.commit()
    return review_id
