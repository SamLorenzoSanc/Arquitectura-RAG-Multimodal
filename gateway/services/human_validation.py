"""Cola HITL: validación humana de respuestas RAG y preguntas extraídas."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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
        keywords = item.get("keywords") or []
        if not isinstance(keywords, list):
            keywords = []
        reference_answer = (item.get("reference_answer") or "").strip() or None
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
                    status, category, filename, rationale
                ) VALUES (
                    :id, 'document_question', :user_id, :organization_id,
                    :document_id, :knowledge_base_id, :question, :answer,
                    :context_snippet, 'pending', :category, :filename, :rationale
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


async def promote_review_to_evaluation_bank(
    db: AsyncSession,
    *,
    document_id: str | None,
    question: str,
    reference_answer: str | None,
    category: str | None = None,
) -> None:
    """Tras aprobar o corregir una pregunta de muestra, entra en el banco RAG."""
    if not document_id or not (question or "").strip():
        return
    from services.evaluation_dataset import insert_extracted_questions_into_bank

    doc = await db.execute(
        text("SELECT tenant_id FROM public.documents WHERE id = :id LIMIT 1"),
        {"id": document_id},
    )
    row = doc.mappings().first()
    if not row or not row.get("tenant_id"):
        return
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
    meta = extra.mappings().first() or {}
    keywords = meta.get("keywords") or []
    if isinstance(keywords, str):
        try:
            keywords = json.loads(keywords)
        except json.JSONDecodeError:
            keywords = []
    await insert_extracted_questions_into_bank(
        db,
        tenant_id=str(row["tenant_id"]),
        questions=[
            {
                "question": question,
                "keywords": keywords if isinstance(keywords, list) else [],
                "reference_answer": reference_answer
                or meta.get("reference_answer")
                or meta.get("rationale")
                or "",
                "category": category or meta.get("category") or "general",
                "out_of_knowledge": (category or meta.get("category"))
                == "out_of_knowledge",
            }
        ],
        document_id=str(document_id),
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
