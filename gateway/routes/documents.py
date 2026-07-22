# routers/documents.py
from __future__ import annotations

import logging
from uuid import uuid4, UUID

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db, AsyncSessionLocal
from services.document_processor import DocumentProcessor
from services.storage_service import StorageService
from .auth import get_current_user
from models import User, Tenant, OrganizationMember, KnowledgeBase, Document
from schemas.document import UploadResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])


async def _run_processing(document_id: UUID) -> None:
    """Processes document in a dedicated background session."""
    async with AsyncSessionLocal() as session:
        try:
            await DocumentProcessor(session).process(document_id)
        except Exception:
            logger.exception("Processing failed for document %s", document_id)


@router.get("")
async def list_documents(
    knowledge_base_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = await db.scalar(select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id))
    if not kb:
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
    if not member:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")

    result = await db.execute(
        select(Document)
        .where(Document.knowledge_base_id == knowledge_base_id)
        .order_by(Document.uploaded_at.desc())
    )
    documents = result.scalars().all()

    return [
        {
            "id": str(doc.id),
            "filename": doc.filename,
            "title": doc.title,
            "description": doc.description,
            "size": doc.size,
            "mime_type": doc.mime_type,
            "current_version": doc.current_version,
            "created_at": doc.uploaded_at,
        }
        for doc in documents
    ]


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    knowledge_base_id: UUID = Form(...),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = await db.scalar(select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id))
    if not kb:
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
    if not member:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    file.file.seek(0, 2)
    size = file.file.tell()
    await file.seek(0)
    if size == 0:
        raise HTTPException(status_code=400, detail="Empty file submitted")

    storage = StorageService()
    try:
        saved_path = await storage.save(
            file=file, tenant_id=kb.tenant_id, knowledge_base_id=kb.id
        )
    except Exception:
        logger.exception("Storage saving failed for file %s", file.filename)
        raise HTTPException(status_code=500, detail="Unable to persist document storage")

    document_id = str(uuid4())
    doc_version_id = str(uuid4())
    job_id = str(uuid4())

    try:
        await db.execute(
            text("""
                INSERT INTO documents (id, tenant_id, knowledge_base_id, owner_id, filename, title, description, mime_type, storage_path, size, current_version, uploaded_at)
                VALUES (:id, :tenant_id, :kb_id, :owner_id, :filename, :title, :desc, :mime, :path, :size, 1, CURRENT_TIMESTAMP)
            """),
            {
                "id": document_id, "tenant_id": str(kb.tenant_id), "kb_id": str(kb.id),
                "owner_id": str(current_user.id), "filename": file.filename, "title": title,
                "desc": description, "mime": file.content_type, "path": str(saved_path), "size": size
            }
        )

        await db.execute(
            text("""
                INSERT INTO document_versions (id, document_id, version, filename, storage_path, uploaded_by, uploaded_at)
                VALUES (:id, :doc_id, 1, :filename, :path, :user_id, CURRENT_TIMESTAMP)
            """),
            {
                "id": doc_version_id, "doc_id": document_id, "filename": file.filename,
                "path": str(saved_path), "user_id": str(current_user.id)
            }
        )

        await db.execute(
            text("""
                INSERT INTO processing_jobs (id, tenant_id, document_id, status, chunks_generated)
                VALUES (:id, :tenant_id, :doc_id, 'PENDING', 0)
            """),
            {"id": job_id, "tenant_id": str(kb.tenant_id), "doc_id": document_id}
        )

        await db.commit()
    except Exception:
        await db.rollback()
        await storage.delete(saved_path)
        raise HTTPException(status_code=500, detail="Database registration failed")

    background_tasks.add_task(_run_processing, UUID(document_id))
    return UploadResponse(id=UUID(document_id), message="Document uploaded successfully")