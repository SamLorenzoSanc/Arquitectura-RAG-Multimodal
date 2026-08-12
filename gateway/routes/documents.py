"""Consulta de metadatos documentales históricos.

El monolito conserva documentos, chunks y embeddings ya existentes para RAG, pero
no admite altas, reindexado, descarga ni eliminación de archivos.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Document, KnowledgeBase, OrganizationMember, ProcessingJob, Tenant, User
from routes.auth import get_current_user
from services.database import get_db

router = APIRouter(prefix="/documents", tags=["Documents"])


async def _validate_kb_access(
    db: AsyncSession,
    knowledge_base_id: UUID,
    current_user: User,
) -> None:
    kb = await db.scalar(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)
    )
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")

    member = await db.scalar(
        select(OrganizationMember)
        .join(Tenant, Tenant.organization_id == OrganizationMember.organization_id)
        .where(
            Tenant.id == kb.tenant_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.active.is_(True),
        )
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")


@router.get("")
async def list_documents(
    knowledge_base_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista metadatos históricos sin acceder al archivo original."""
    await _validate_kb_access(db, knowledge_base_id, current_user)

    documents = (
        await db.scalars(
            select(Document)
            .where(Document.knowledge_base_id == knowledge_base_id)
            .order_by(Document.uploaded_at.desc())
        )
    ).all()

    response = []
    for document in documents:
        job = await db.scalar(
            select(ProcessingJob)
            .where(ProcessingJob.document_id == document.id)
            .order_by(ProcessingJob.id.desc())
        )
        processing_status = (job.status or "uploaded").lower() if job else "uploaded"
        updated_at = (
            getattr(job, "finished_at", None)
            or getattr(job, "started_at", None)
            or document.uploaded_at
        )
        response.append(
            {
                "id": str(document.id),
                "filename": document.filename,
                "name": document.title or document.filename,
                "title": document.title,
                "description": document.description,
                "size": document.size,
                "mime_type": document.mime_type,
                "content_type": document.mime_type,
                "current_version": document.current_version,
                "created_at": document.uploaded_at,
                "updated_at": updated_at,
                "status": "active" if processing_status == "completed" else "inactive",
                "processing_status": processing_status,
                "active": processing_status == "completed",
                "job_id": str(job.id) if job else None,
                "chunks": getattr(job, "chunks_generated", 0) if job else 0,
                "attempts": getattr(job, "attempts", 0) if job else 0,
                "embedding_model": getattr(job, "embedding_model", None) if job else None,
                "generation_model": getattr(job, "llm_model", None) if job else None,
                "llm_model": getattr(job, "llm_model", None) if job else None,
                "error": getattr(job, "error_message", None) if job else None,
            }
        )

    return response
