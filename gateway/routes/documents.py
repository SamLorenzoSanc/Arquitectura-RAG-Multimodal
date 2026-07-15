from __future__ import annotations

import logging
from uuid import uuid4, UUID

from fastapi import (
    APIRouter, UploadFile, File, Form, HTTPException,
    Depends, BackgroundTasks, status,
)
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db, AsyncSessionLocal
from services.document_processor import DocumentProcessor
from services.storage_service import StorageService

from .auth import get_current_user

from models.user import User
from models.tenant import Tenant
from models.organization_member import OrganizationMember
from models.document import Document
from models.document_version import DocumentVersion
from models.processing_job import ProcessingJob
from models.knowledge_base import KnowledgeBase
# from models.knowledge_base_permission import KnowledgeBasePermission  # (ver nota)

from schemas.document import UploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])


async def _run_processing(document_id: UUID) -> None:
    """Corre tras enviar la respuesta, con su PROPIA sesión."""
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
    # Verificar que la KB existe
    kb = await db.scalar(
        select(KnowledgeBase).where(
            KnowledgeBase.id == knowledge_base_id
        )
    )

    if kb is None:
        raise HTTPException(404, "Knowledge Base not found")

    # Comprobar permisos exactamente igual que en upload
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
        raise HTTPException(404, "Knowledge Base not found")

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
    kb = await db.scalar(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)
    )
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")

    # --- permiso multi-tenant -------------------------------------------
    # ¿es current_user miembro activo de la organización dueña del tenant
    # de esta KB?  kb.tenant_id -> tenants.organization_id -> members
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
        # 404 en vez de 403 para no revelar la existencia de la KB a quien no tiene acceso
        raise HTTPException(status_code=404, detail="Knowledge Base not found")

    # (opcional, más fino) exigir permiso de escritura sobre ESTA KB:
    # perm = await db.scalar(
    #     select(KnowledgeBasePermission).where(
    #         KnowledgeBasePermission.knowledge_base_id == kb.id,
    #         KnowledgeBasePermission.member_id == member.id,
    #         KnowledgeBasePermission.permission.in_(["write", "admin"]),
    #     )
    # )
    # if perm is None:
    #     raise HTTPException(status_code=403, detail="No write permission on this KB")
    # --------------------------------------------------------------------

    if file.filename is None:
        raise HTTPException(status_code=400, detail="Filename is required")

    file.file.seek(0, 2)
    size = file.file.tell()
    await file.seek(0)
    if size == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    storage = StorageService()
    try:
        saved_path = await storage.save(
            file=file, tenant_id=kb.tenant_id, knowledge_base_id=kb.id,
        )
    except Exception:
        logger.exception("Storage failed for %s", file.filename)
        raise HTTPException(status_code=500, detail="Cannot store document")

    document_id = str(uuid4())


    await db.execute(
        text("""
            INSERT INTO documents
            (
                id,
                tenant_id,
                knowledge_base_id,
                owner_id,
                filename,
                title,
                description,
                mime_type,
                storage_path,
                size,
                current_version,
                uploaded_at
            )
            VALUES
            (
                :id,
                :tenant_id,
                :knowledge_base_id,
                :owner_id,
                :filename,
                :title,
                :description,
                :mime_type,
                :storage_path,
                :size,
                :current_version,
                CURRENT_TIMESTAMP
            )
        """),
        {
            "id": document_id,
            "tenant_id": str(kb.tenant_id),
            "knowledge_base_id": str(kb.id),
            "owner_id": str(current_user.id),
            "filename": file.filename,
            "title": title,
            "description": description,
            "mime_type": file.content_type,
            "storage_path": str(saved_path),
            "size": size,
            "current_version": 1,
        }
    )

    document_version_id = str(uuid4())


    await db.execute(
        text("""
            INSERT INTO document_versions
            (
                id,
                document_id,
                version,
                filename,
                storage_path,
                uploaded_by,
                uploaded_at
            )
            VALUES
            (
                :id,
                :document_id,
                :version,
                :filename,
                :storage_path,
                :uploaded_by,
                CURRENT_TIMESTAMP
            )
        """),
        {
            "id": document_version_id,
            "document_id": document_id,
            "version": 1,
            "filename": file.filename,
            "storage_path": str(saved_path),
            "uploaded_by": str(current_user.id),
        }
    )

    processing_job_id = str(uuid4())

    await db.execute(
        text("""
            INSERT INTO processing_jobs
            (
                id,
                tenant_id,
                document_id,
                status,
                chunks_generated
            )
            VALUES
            (
                :id,
                :tenant_id,
                :document_id,
                :status,
                :chunks_generated
            )
        """),
        {
            "id": processing_job_id,
            "tenant_id": str(kb.tenant_id),
            "document_id": document_id,
            "status": "PENDING",
            "chunks_generated": 0,
        }
    )

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        await storage.delete(saved_path)
        raise HTTPException(status_code=500, detail="Cannot register document")

    background_tasks.add_task(_run_processing, UUID(document_id))


    return UploadResponse(id=UUID(document_id), message="Document uploaded successfully")