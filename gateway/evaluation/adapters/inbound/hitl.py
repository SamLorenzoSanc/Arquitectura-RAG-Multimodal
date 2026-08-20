from typing import Any, Literal, Optional
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db
from evaluation.application import hitl
from identity.adapters.inbound.auth import get_current_user

router = APIRouter(prefix="/human-validation", tags=["Human validation"])

ReviewStatus = Literal["pending", "approved", "rejected", "corrected"]


class ReviewDecision(BaseModel):
    status: Literal["approved", "rejected", "corrected"]
    reviewer_notes: Optional[str] = None
    corrected_answer: Optional[str] = Field(default=None, max_length=8000)
    question: Optional[str] = Field(default=None, max_length=2000)
    keywords: list[str] = Field(default_factory=list)
    category: Optional[str] = Field(default=None, max_length=80)


@router.get("/reviews", status_code=200)
async def list_reviews(
    status: Optional[str] = Query("pending"),
    source: Optional[str] = Query("document_question"),
    organization_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await hitl.init_human_validation_tables(db)
    clauses = ["1=1"]
    params: dict[str, Any] = {"limit": limit}
    if status and status != "all":
        clauses.append("status = :status")
        params["status"] = status
    if source and source != "all":
        clauses.append("source = :source")
        params["source"] = source
    if organization_id:
        clauses.append(
            "(organization_id = :organization_id OR organization_id IS NULL)"
        )
        params["organization_id"] = organization_id
    result = await db.execute(
        text(f"""
            SELECT id, source, user_id, organization_id, conversation_id,
                   document_id, knowledge_base_id, question, answer,
                   context_snippet, chunk_ids, status, corrected_answer,
                   reviewer_notes, reviewer_id, created_at, reviewed_at,
                   category, filename, rationale, keywords
            FROM rag_human_reviews
            WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC
            LIMIT :limit
            """),
        params,
    )
    rows = [hitl._serialize(dict(r)) for r in result.mappings().all()]
    pending = sum(1 for r in rows if r.get("status") == "pending")
    return {"count": len(rows), "pending": pending, "data": rows}


@router.post("/reviews/{review_id}", status_code=200)
async def decide_review(
    review_id: str,
    data: ReviewDecision,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await hitl.init_human_validation_tables(db)
    if data.status == "corrected" and not (data.corrected_answer or "").strip():
        raise HTTPException(
            status_code=400, detail="La corrección necesita un texto de respuesta"
        )
    result = await db.execute(
        text("""
            UPDATE rag_human_reviews
            SET status = :status,
                reviewer_notes = :reviewer_notes,
                corrected_answer = :corrected_answer,
                reviewer_id = :reviewer_id,
                reviewed_at = CURRENT_TIMESTAMP,
                question = COALESCE(:question, question),
                category = COALESCE(:category, category),
                keywords = CASE
                    WHEN CAST(:has_keywords AS boolean)
                    THEN CAST(:keywords AS jsonb)
                    ELSE COALESCE(keywords, '[]'::jsonb)
                END
            WHERE id = :id
            """),
        {
            "id": review_id,
            "status": data.status,
            "reviewer_notes": (data.reviewer_notes or "").strip() or None,
            "corrected_answer": (data.corrected_answer or "").strip() or None,
            "reviewer_id": str(current_user.id),
            "question": (data.question or "").strip() or None,
            "category": (data.category or "").strip() or None,
            "has_keywords": bool(data.keywords),
            "keywords": json.dumps(
                [str(item).strip() for item in data.keywords if str(item).strip()],
                ensure_ascii=False,
            ),
        },
    )
    if result.rowcount == 0:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Revisión no encontrada")

    review = await db.execute(
        text("""
            SELECT document_id, question, source, answer, category, filename,
                   organization_id, knowledge_base_id, keywords, corrected_answer
            FROM rag_human_reviews WHERE id = :id
            """),
        {"id": review_id},
    )
    row = review.mappings().first()
    if row and row.get("document_id") and row.get("question"):
        q_status = (
            "approved" if data.status in ("approved", "corrected") else "rejected"
        )
        await db.execute(
            text("""
                UPDATE document_questions
                SET status = :status,
                    reviewer_notes = :notes,
                    reviewed_at = CURRENT_TIMESTAMP,
                    reference_answer = COALESCE(:reference_answer, reference_answer),
                    category = COALESCE(:category, category),
                    keywords = CASE
                        WHEN CAST(:has_keywords AS boolean)
                        THEN CAST(:keywords AS jsonb)
                        ELSE keywords
                    END
                WHERE document_id = :document_id AND question = :question
                """),
            {
                "status": q_status,
                "notes": (data.reviewer_notes or "").strip() or None,
                "reference_answer": (data.corrected_answer or "").strip() or None,
                "category": (data.category or "").strip() or None,
                "has_keywords": bool(data.keywords),
                "keywords": json.dumps(
                    [str(item).strip() for item in data.keywords if str(item).strip()],
                    ensure_ascii=False,
                ),
                "document_id": str(row["document_id"]),
                "question": row["question"],
            },
        )
    if row and row.get("question") and data.status in ("approved", "corrected"):
        await hitl.promote_review_to_evaluation_bank(
            db,
            document_id=str(row["document_id"]) if row.get("document_id") else None,
            organization_id=str(row["organization_id"]) if row.get("organization_id") else None,
            question=(data.question or row.get("question") or ""),
            reference_answer=(
                data.corrected_answer
                or row.get("corrected_answer")
                or row.get("answer")
                or ""
            ),
            category=data.category or row.get("category"),
            keywords=data.keywords or row.get("keywords") or [],
            filename=row.get("filename"),
        )
    elif row and row.get("document_id") and data.status == "rejected":
        doc = await db.execute(
            text("SELECT tenant_id FROM public.documents WHERE id = :id LIMIT 1"),
            {"id": str(row["document_id"])},
        )
        tenant = doc.mappings().first()
        if tenant and tenant.get("tenant_id"):
            from services.evaluation_dataset import remove_hitl_question_from_bank

            await remove_hitl_question_from_bank(
                db,
                tenant_id=str(tenant["tenant_id"]),
                question=row["question"],
            )
    if row and row.get("source") == "synthetic_dataset" and row.get("question"):
        row_status = (
            "approved" if data.status in ("approved", "corrected") else "rejected"
        )
        await db.execute(
            text("""
                UPDATE rag_dataset_rows
                SET status = :status,
                    expected_response = COALESCE(:corrected_answer, expected_response)
                WHERE organization_id = :organization_id
                  AND knowledge_base_id IS NOT DISTINCT FROM :knowledge_base_id
                  AND prompt = :question
                  AND source = 'synthetic'
                """),
            {
                "status": row_status,
                "corrected_answer": (data.corrected_answer or "").strip() or None,
                "organization_id": row.get("organization_id"),
                "knowledge_base_id": row.get("knowledge_base_id"),
                "question": row["question"],
            },
        )
        await db.execute(
            text("""
                UPDATE rag_datasets AS dataset
                SET status = CASE
                    WHEN EXISTS (
                        SELECT 1 FROM rag_dataset_rows AS item
                        WHERE item.dataset_id = dataset.id
                          AND item.status = 'pending_review'
                    ) THEN 'pending_review'
                    ELSE 'ready'
                END,
                updated_at = CURRENT_TIMESTAMP
                WHERE dataset.organization_id = :organization_id
                  AND dataset.knowledge_base_id IS NOT DISTINCT FROM :knowledge_base_id
                  AND dataset.source_type = 'synthetic'
                """),
            {
                "organization_id": row.get("organization_id"),
                "knowledge_base_id": row.get("knowledge_base_id"),
            },
        )
    await db.commit()
    return {"status": "success", "id": review_id, "decision": data.status}


@router.get("/questions", status_code=200)
async def list_document_questions(
    knowledge_base_id: Optional[str] = Query(None),
    document_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await hitl.init_human_validation_tables(db)
    clauses = ["1=1"]
    params: dict[str, Any] = {}
    if knowledge_base_id:
        clauses.append("knowledge_base_id = :knowledge_base_id")
        params["knowledge_base_id"] = knowledge_base_id
    if document_id:
        clauses.append("document_id = :document_id")
        params["document_id"] = document_id
    result = await db.execute(
        text(f"""
            SELECT id, document_id, knowledge_base_id, question, rationale,
                   category, keywords, reference_answer, filename,
                   status, created_at, reviewed_at, reviewer_notes
            FROM document_questions
            WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC
            LIMIT 200
            """),
        params,
    )
    rows = [hitl._serialize(dict(r)) for r in result.mappings().all()]
    return {"count": len(rows), "data": rows}


@router.post("/extract-missing", status_code=202)
async def extract_missing_questions(
    background_tasks: BackgroundTasks,
    organization_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
):
    """Encola preguntas HITL para documentos indexados que aún no tienen muestra."""

    background_tasks.add_task(
        hitl.enqueue_missing_document_eval_questions,
        organization_id=organization_id,
        limit=8,
    )
    return {"status": "queued", "organization_id": organization_id}
