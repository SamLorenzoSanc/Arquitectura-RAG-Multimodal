from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Document,
    DocumentVersion,
    KnowledgeBase,
    OrganizationMember,
    ProcessingJob,
    Tenant,
    User,
)

from schemas.document import UploadResponse

from services.database import (
    AsyncSessionLocal,
    get_db,
)

from services.document_processor import (
    DocumentProcessor,
)

from services.storage_service import (
    StorageService,
)

from .auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


# ============================================================
# BACKGROUND PROCESSING
# ============================================================


async def _run_processing(
    document_id: UUID,
    job_id: UUID,
) -> None:
    """
    Ejecuta la indexación RAG en una sesión independiente.

    IMPORTANTE:
    La subida del documento NO llama a esta función.
    Solo el endpoint /{document_id}/index la ejecuta.
    """

    async with AsyncSessionLocal() as session:

        try:

            # ------------------------------------------------
            # Marcar job como RUNNING
            # ------------------------------------------------

            job = await session.scalar(
                select(ProcessingJob).where(ProcessingJob.id == job_id)
            )

            if not job:
                logger.error(
                    "ProcessingJob %s not found",
                    job_id,
                )
                return

            job.status = "RUNNING"

            await session.commit()

            logger.info(
                "[RAG INDEX] Starting document=%s job=%s",
                document_id,
                job_id,
            )

            # ------------------------------------------------
            # Ejecutar pipeline
            # ------------------------------------------------

            processor = DocumentProcessor(session)

            await processor.process(document_id)

            # ------------------------------------------------
            # COMPLETED
            # ------------------------------------------------

            job = await session.scalar(
                select(ProcessingJob).where(ProcessingJob.id == job_id)
            )

            if job:
                job.status = "COMPLETED"

                await session.commit()

            logger.info(
                "[RAG INDEX] Completed document=%s",
                document_id,
            )

        except Exception as exc:

            logger.exception(
                "[RAG INDEX] Failed document=%s",
                document_id,
            )

            try:

                job = await session.scalar(
                    select(ProcessingJob).where(ProcessingJob.id == job_id)
                )

                if job:

                    job.status = "FAILED"

                    await session.commit()

            except Exception:

                logger.exception(
                    "Could not update failed job %s",
                    job_id,
                )


# ============================================================
# AUTHORIZATION HELPER
# ============================================================


async def _validate_kb_access(
    db: AsyncSession,
    knowledge_base_id: UUID,
    current_user: User,
) -> KnowledgeBase:

    kb = await db.scalar(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)
    )

    if not kb:

        raise HTTPException(
            status_code=404,
            detail="Knowledge Base not found",
        )

    member = await db.scalar(
        select(OrganizationMember)
        .join(
            Tenant,
            Tenant.organization_id == OrganizationMember.organization_id,
        )
        .where(
            Tenant.id == kb.tenant_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.active.is_(True),
        )
    )

    if not member:

        raise HTTPException(
            status_code=404,
            detail="Knowledge Base not found",
        )

    return kb


# ============================================================
# LIST DOCUMENTS
# ============================================================


@router.get("")
async def list_documents(
    knowledge_base_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    kb = await _validate_kb_access(
        db,
        knowledge_base_id,
        current_user,
    )

    result = await db.execute(
        select(Document)
        .where(Document.knowledge_base_id == knowledge_base_id)
        .order_by(Document.uploaded_at.desc())
    )

    documents = result.scalars().all()

    response = []

    for doc in documents:

        # ----------------------------------------------------
        # Último ProcessingJob
        # ----------------------------------------------------

        job = await db.scalar(
            select(ProcessingJob)
            .where(ProcessingJob.document_id == doc.id)
            .order_by(ProcessingJob.id.desc())
        )

        response.append(
            {
                "id": str(doc.id),
                "filename": doc.filename,
                "name": (doc.title or doc.filename),
                "title": doc.title,
                "description": doc.description,
                "size": doc.size,
                "mime_type": doc.mime_type,
                "content_type": doc.mime_type,
                "current_version": doc.current_version,
                "created_at": doc.uploaded_at,
                "updated_at": doc.uploaded_at,
                # -------------------------------
                # RAG
                # -------------------------------
                "status": (job.status.lower() if job else "uploaded"),
                "chunks": (job.chunks_generated if job else 0),
                "attempts": 0,
                "error": None,
            }
        )

    return response


@router.post("/{document_id}/index")
async def index_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ---------------------------------------------------------
    # 1. BUSCAR DOCUMENTO
    # ---------------------------------------------------------

    document = await db.scalar(select(Document).where(Document.id == document_id))

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # ---------------------------------------------------------
    # 2. VALIDAR PERMISOS
    # ---------------------------------------------------------

    kb = await db.scalar(
        select(KnowledgeBase).where(KnowledgeBase.id == document.knowledge_base_id)
    )

    if not kb:
        raise HTTPException(
            status_code=404,
            detail="Knowledge Base not found",
        )

    member = await db.scalar(
        select(OrganizationMember)
        .join(
            Tenant,
            Tenant.organization_id == OrganizationMember.organization_id,
        )
        .where(
            Tenant.id == kb.tenant_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.active.is_(True),
        )
    )

    if not member:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # ---------------------------------------------------------
    # 3. BUSCAR JOB
    # ---------------------------------------------------------

    job = await db.scalar(
        select(ProcessingJob)
        .where(ProcessingJob.document_id == document_id)
        .order_by(ProcessingJob.id.desc())
    )

    if not job:
        job = ProcessingJob(
            id=uuid4(),
            tenant_id=document.tenant_id,
            document_id=document.id,
            status="PENDING",
            chunks_generated=0,
        )

        db.add(job)

    else:
        job.status = "PENDING"
        job.chunks_generated = 0

    await db.commit()

    # ---------------------------------------------------------
    # 4. LANZAR INDEXACIÓN
    # ---------------------------------------------------------

    background_tasks.add_task(
        _run_processing,
        document_id,
    )

    return {
        "document_id": str(document_id),
        "status": "indexing",
        "message": "Document indexing started",
    }


# ============================================================
# UPLOAD
# ============================================================


@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    knowledge_base_id: UUID = Form(...),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ---------------------------------------------------------
    # 1. VALIDAR KNOWLEDGE BASE
    # ---------------------------------------------------------

    kb = await db.scalar(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)
    )

    if not kb:
        raise HTTPException(
            status_code=404,
            detail="Knowledge Base not found",
        )

    # ---------------------------------------------------------
    # 2. VALIDAR PERMISOS
    # ---------------------------------------------------------

    member = await db.scalar(
        select(OrganizationMember)
        .join(
            Tenant,
            Tenant.organization_id == OrganizationMember.organization_id,
        )
        .where(
            Tenant.id == kb.tenant_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.active.is_(True),
        )
    )

    if not member:
        raise HTTPException(
            status_code=404,
            detail="Knowledge Base not found",
        )

    # ---------------------------------------------------------
    # 3. VALIDAR ARCHIVO
    # ---------------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    size = file.size or 0

    if size == 0:
        await file.seek(0, 2)
        size = file.tell()
        await file.seek(0)

    if size == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file submitted",
        )

    # ---------------------------------------------------------
    # 4. GUARDAR FÍSICAMENTE EL ARCHIVO
    # ---------------------------------------------------------

    storage = StorageService()

    try:
        saved_path = await storage.save(
            file=file,
            tenant_id=kb.tenant_id,
            knowledge_base_id=kb.id,
        )

    except Exception:
        logger.exception(
            "Storage saving failed for file %s",
            file.filename,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to persist document storage",
        )

    # ---------------------------------------------------------
    # 5. CREAR DOCUMENTO
    # ---------------------------------------------------------

    doc_id = uuid4()

    try:
        document = Document(
            id=doc_id,
            tenant_id=kb.tenant_id,
            knowledge_base_id=kb.id,
            owner_id=current_user.id,
            filename=file.filename,
            title=title or file.filename,
            description=description,
            mime_type=file.content_type or "application/octet-stream",
            storage_path=str(saved_path),
            size=size,
            current_version=1,
        )

        db.add(document)

        # -----------------------------------------------------
        # 6. CREAR VERSION
        # -----------------------------------------------------

        doc_version = DocumentVersion(
            id=uuid4(),
            document_id=doc_id,
            version=1,
            filename=file.filename,
            storage_path=str(saved_path),
            uploaded_by=current_user.id,
        )

        db.add(doc_version)

        # -----------------------------------------------------
        # 7. CREAR JOB PENDIENTE
        # -----------------------------------------------------

        job = ProcessingJob(
            id=uuid4(),
            tenant_id=kb.tenant_id,
            document_id=doc_id,
            status="PENDING",
            chunks_generated=0,
        )

        db.add(job)

        await db.commit()

    except Exception:
        await db.rollback()

        try:
            await storage.delete(saved_path)
        except Exception:
            logger.exception("Could not delete storage file after DB failure")

        logger.exception("Failed to persist document records in DB")

        raise HTTPException(
            status_code=500,
            detail="Database registration failed",
        )

    # ---------------------------------------------------------
    # IMPORTANTE:
    #
    # NO lanzar DocumentProcessor aquí.
    #
    # La indexación se hará posteriormente mediante:
    #
    # POST /documents/{document_id}/index
    # ---------------------------------------------------------

    return UploadResponse(
        id=doc_id,
        message="Document uploaded successfully. Waiting for indexing.",
    )


# ============================================================
# START INDEXING
# ============================================================


@router.post(
    "/{document_id}/index",
    status_code=status.HTTP_202_ACCEPTED,
)
async def index_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # ========================================================
    # DOCUMENT
    # ========================================================

    document = await db.scalar(select(Document).where(Document.id == document_id))

    if not document:

        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # ========================================================
    # ACCESS
    # ========================================================

    await _validate_kb_access(
        db,
        document.knowledge_base_id,
        current_user,
    )

    # ========================================================
    # CHECK ACTIVE JOB
    # ========================================================

    active_job = await db.scalar(
        select(ProcessingJob).where(
            ProcessingJob.document_id == document_id,
            ProcessingJob.status.in_(
                [
                    "PENDING",
                    "RUNNING",
                ]
            ),
        )
    )

    if active_job:

        return {
            "document_id": str(document_id),
            "job_id": str(active_job.id),
            "status": active_job.status,
            "message": "Document indexing already running",
        }

    # ========================================================
    # NEW JOB
    #
    # Esto permite REINDEXAR.
    # ========================================================

    job = ProcessingJob(
        id=uuid4(),
        tenant_id=document.tenant_id,
        document_id=document.id,
        status="PENDING",
        chunks_generated=0,
    )

    db.add(job)

    await db.commit()

    # ========================================================
    # LAUNCH BACKGROUND JOB
    # ========================================================

    background_tasks.add_task(
        _run_processing,
        document.id,
        job.id,
    )

    logger.info(
        "[RAG INDEX] Queued document=%s job=%s",
        document.id,
        job.id,
    )

    return {
        "document_id": str(document.id),
        "job_id": str(job.id),
        "status": "PENDING",
        "message": "Document indexing started",
    }


# ============================================================
# PROGRESS / SSE
# ============================================================


@router.get("/{document_id}/progress")
async def get_document_progress(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # ========================================================
    # DOCUMENT
    # ========================================================

    document = await db.scalar(select(Document).where(Document.id == document_id))

    if not document:

        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # ========================================================
    # AUTHORIZATION
    # ========================================================

    await _validate_kb_access(
        db,
        document.knowledge_base_id,
        current_user,
    )

    # ========================================================
    # SSE
    # ========================================================

    async def event_generator():

        last_status = None
        last_chunks = None

        while True:

            # ------------------------------------------------
            # Obtener último job
            # ------------------------------------------------

            job = await db.scalar(
                select(ProcessingJob)
                .where(ProcessingJob.document_id == document_id)
                .order_by(ProcessingJob.id.desc())
            )

            if not job:

                payload = {
                    "document_id": str(document_id),
                    "status": "UPLOADED",
                    "step": "upload",
                    "detail": "Documento subido. Pendiente de indexación.",
                    "chunks": 0,
                }

                yield ("data: " + json.dumps(payload) + "\n\n")

                await asyncio.sleep(2)

                continue

            # ------------------------------------------------
            # Status
            # ------------------------------------------------

            status_value = job.status or "UNKNOWN"

            chunks = job.chunks_generated or 0

            # ------------------------------------------------
            # Solo enviar cambios
            # ------------------------------------------------

            if status_value != last_status or chunks != last_chunks:

                if status_value == "PENDING":

                    step = "pending"

                    detail = "Documento pendiente " "de procesamiento."

                elif status_value == "RUNNING":

                    step = "indexing"

                    detail = "Procesando documento " "e indexando contenido."

                elif status_value == "COMPLETED":

                    step = "finish"

                    detail = "Documento indexado " "correctamente."

                elif status_value == "FAILED":

                    step = "error"

                    detail = "La indexación " "ha fallado."

                else:

                    step = "unknown"

                    detail = f"Estado: " f"{status_value}"

                payload = {
                    "document_id": str(document_id),
                    "job_id": str(job.id),
                    "status": status_value,
                    "step": step,
                    "detail": detail,
                    "chunks": chunks,
                }

                yield ("data: " + json.dumps(payload) + "\n\n")

                last_status = status_value

                last_chunks = chunks

            # ------------------------------------------------
            # Terminado
            # ------------------------------------------------

            if status_value in {
                "COMPLETED",
                "FAILED",
            }:

                break

            # ------------------------------------------------
            # Polling
            # ------------------------------------------------

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
