from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
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
from services.ingest_service import (
    EMBEDDING_MODEL,
    MODEL,
    IngestService,
)
from services.storage_service import StorageService
from .auth import get_current_user
from models.chunk import Chunk
from models.embedding import Embedding

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

# Los documentos normales siguen usando el parser existente.
# Los vídeos se detectan además por extensión para soportar casos
# donde el navegador envía application/octet-stream.
VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".mpeg",
    ".mpg",
    ".m4v",
}

VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/matroska",
    "video/x-matroska",
    "video/webm",
    "video/mpeg",
    "video/x-m4v",
}


# ============================================================
# HELPERS
# ============================================================


def _utcnow():
    """
    Devuelve datetime UTC.

    Se mantiene en una función para que el código sea compatible
    con modelos que tengan started_at/finished_at como columnas
    opcionales.
    """
    return datetime.now(timezone.utc)


def _set_if_attribute(obj, attribute: str, value) -> bool:
    """
    Asigna un atributo únicamente si el modelo SQLAlchemy lo tiene.

    Esto permite que este documents.py funcione también si una
    instalación antigua todavía no tiene alguna de las columnas
    opcionales del ProcessingJob.
    """
    if hasattr(obj, attribute):
        setattr(obj, attribute, value)
        return True
    return False


def _normalise_mime_type(value: str | None) -> str:
    return (value or "").lower().split(";")[0].strip()


def _is_video_file(
    filename: str | None,
    mime_type: str | None,
) -> bool:
    suffix = ""
    if filename:
        # Evitamos importar mimetypes solamente para esta comprobación.
        dot_index = filename.rfind(".")
        if dot_index >= 0:
            suffix = filename[dot_index:].lower()

    return (
        _normalise_mime_type(mime_type) in VIDEO_MIME_TYPES
        or suffix in VIDEO_EXTENSIONS
    )


def _job_status_for_frontend(job: ProcessingJob | None) -> str:
    """
    Estado visual solicitado por el frontend.

    COMPLETED -> active
    Cualquier otro estado -> inactive

    El estado técnico se expone por separado como processing_status.
    """
    if job and (job.status or "").upper() == "COMPLETED":
        return "active"

    return "inactive"


def _processing_status(job: ProcessingJob | None) -> str:
    if not job:
        return "uploaded"

    return (job.status or "UNKNOWN").lower()


def _job_error(job: ProcessingJob | None):
    if not job:
        return None

    return getattr(job, "error_message", None)


def _job_updated_at(
    document: Document,
    job: ProcessingJob | None,
):
    if job:
        finished_at = getattr(job, "finished_at", None)
        if finished_at:
            return finished_at

        started_at = getattr(job, "started_at", None)
        if started_at:
            return started_at

    return document.uploaded_at


def _job_attempts(job: ProcessingJob | None) -> int:
    if not job:
        return 0

    return int(getattr(job, "attempts", 0) or 0)


# ============================================================
# BACKGROUND PROCESSING
# ============================================================


async def _run_processing(
    document_id: UUID,
    job_id: UUID,
) -> None:
    """
    Ejecuta la indexación RAG en una sesión independiente.

    Pipeline:

        documento:
            parser -> Markdown -> chunks -> LLM -> embeddings -> BM25

        vídeo:
            vídeo -> FFmpeg -> Whisper -> resumen -> Markdown
                  -> chunks -> LLM -> embeddings -> BM25

    El endpoint de upload crea el ProcessingJob y esta función se
    ejecuta en BackgroundTasks después de devolver la respuesta HTTP.
    """

    async with AsyncSessionLocal() as session:
        try:
            # --------------------------------------------------------
            # BUSCAR JOB
            # --------------------------------------------------------

            job = await session.scalar(
                select(ProcessingJob).where(ProcessingJob.id == job_id)
            )

            if not job:
                logger.error(
                    "ProcessingJob %s not found",
                    job_id,
                )
                return

            # --------------------------------------------------------
            # BUSCAR DOCUMENTO
            # --------------------------------------------------------

            document = await session.scalar(
                select(Document).where(Document.id == document_id)
            )

            if not document:
                logger.error(
                    "Document %s not found for job %s",
                    document_id,
                    job_id,
                )

                job.status = "FAILED"
                _set_if_attribute(
                    job,
                    "error_message",
                    "Document not found",
                )
                _set_if_attribute(
                    job,
                    "finished_at",
                    _utcnow(),
                )

                await session.commit()
                return

            # --------------------------------------------------------
            # RUNNING
            # --------------------------------------------------------

            job.status = "RUNNING"

            _set_if_attribute(
                job,
                "started_at",
                _utcnow(),
            )

            # Guardamos los modelos realmente utilizados por la ingesta.
            _set_if_attribute(
                job,
                "embedding_model",
                EMBEDDING_MODEL,
            )

            _set_if_attribute(
                job,
                "llm_model",
                MODEL,
            )

            _set_if_attribute(
                job,
                "error_message",
                None,
            )

            await session.commit()

            logger.info(
                "[RAG INDEX] Starting document=%s job=%s "
                "generation_model=%s embedding_model=%s",
                document_id,
                job_id,
                MODEL,
                EMBEDDING_MODEL,
            )

            # --------------------------------------------------------
            # EJECUTAR INGEST SERVICE
            # --------------------------------------------------------

            ingest_service = IngestService(session)

            chunks_generated = await ingest_service.process(document)

            # --------------------------------------------------------
            # COMPLETED
            # --------------------------------------------------------

            job = await session.scalar(
                select(ProcessingJob).where(ProcessingJob.id == job_id)
            )

            if job:
                job.status = "COMPLETED"
                job.chunks_generated = chunks_generated

                _set_if_attribute(
                    job,
                    "finished_at",
                    _utcnow(),
                )

                _set_if_attribute(
                    job,
                    "embedding_model",
                    EMBEDDING_MODEL,
                )

                _set_if_attribute(
                    job,
                    "llm_model",
                    MODEL,
                )

                _set_if_attribute(
                    job,
                    "error_message",
                    None,
                )

                await session.commit()

            logger.info(
                "[RAG INDEX] Completed document=%s job=%s chunks=%s",
                document_id,
                job_id,
                chunks_generated,
            )

        except asyncio.CancelledError:
            logger.warning(
                "[RAG INDEX] Cancelled document=%s job=%s",
                document_id,
                job_id,
            )

            try:
                job = await session.scalar(
                    select(ProcessingJob).where(ProcessingJob.id == job_id)
                )

                if job:
                    job.status = "FAILED"

                    _set_if_attribute(
                        job,
                        "error_message",
                        "Processing task cancelled",
                    )

                    _set_if_attribute(
                        job,
                        "finished_at",
                        _utcnow(),
                    )

                    await session.commit()

            except Exception:
                logger.exception(
                    "Could not update cancelled job %s",
                    job_id,
                )

            raise

        except Exception as exc:
            logger.exception(
                "[RAG INDEX] Failed document=%s job=%s",
                document_id,
                job_id,
            )

            try:
                job = await session.scalar(
                    select(ProcessingJob).where(ProcessingJob.id == job_id)
                )

                if job:
                    job.status = "FAILED"

                    _set_if_attribute(
                        job,
                        "error_message",
                        str(exc)[:4000],
                    )

                    _set_if_attribute(
                        job,
                        "finished_at",
                        _utcnow(),
                    )

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
    """
    Comprueba que la Knowledge Base existe y que el usuario
    pertenece activamente a la organización del tenant.
    """

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
    """
    Lista los documentos de una Knowledge Base.

    El frontend recibe:

        status:
            active / inactive

        processing_status:
            pending / running / completed / failed / uploaded

        embedding_model:
            modelo usado para generar embeddings

        generation_model:
            modelo usado para enriquecimiento/resumen/generación

        updated_at:
            última actualización conocida del procesamiento

        error:
            mensaje de error si el job ha fallado
    """

    await _validate_kb_access(
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
        # ÚLTIMO PROCESSING JOB
        # ----------------------------------------------------

        job = await db.scalar(
            select(ProcessingJob)
            .where(ProcessingJob.document_id == doc.id)
            .order_by(ProcessingJob.id.desc())
        )

        processing_status = _processing_status(job)

        response.append(
            {
                # ---------------------------------------------
                # Identificación
                # ---------------------------------------------
                "id": str(doc.id),
                "filename": doc.filename,
                "name": (doc.title or doc.filename),
                "title": doc.title,
                "description": doc.description,
                # ---------------------------------------------
                # Archivo
                # ---------------------------------------------
                "size": doc.size,
                "mime_type": doc.mime_type,
                "content_type": doc.mime_type,
                "current_version": doc.current_version,
                # ---------------------------------------------
                # Fechas
                # ---------------------------------------------
                "created_at": doc.uploaded_at,
                "updated_at": _job_updated_at(
                    doc,
                    job,
                ),
                # ---------------------------------------------
                # Estado visual
                # ---------------------------------------------
                # Lo que debe utilizar la tabla:
                # "active" / "inactive"
                "status": _job_status_for_frontend(job),
                # Estado técnico real del pipeline.
                "processing_status": processing_status,
                # Booleano útil para el frontend.
                "active": (processing_status == "completed"),
                # ---------------------------------------------
                # Job
                # ---------------------------------------------
                "job_id": (str(job.id) if job else None),
                "chunks": (job.chunks_generated if job else 0),
                "attempts": _job_attempts(job),
                # ---------------------------------------------
                # Modelos
                # ---------------------------------------------
                "embedding_model": (
                    getattr(
                        job,
                        "embedding_model",
                        None,
                    )
                    or EMBEDDING_MODEL
                ),
                "generation_model": (
                    getattr(
                        job,
                        "llm_model",
                        None,
                    )
                    or MODEL
                ),
                # Alias para clientes que prefieran llm_model.
                "llm_model": (
                    getattr(
                        job,
                        "llm_model",
                        None,
                    )
                    or MODEL
                ),
                # ---------------------------------------------
                # Error
                # ---------------------------------------------
                "error": _job_error(job),
            }
        )

    return response


# ============================================================
# START INDEXING / REINDEX
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
    """
    Lanza manualmente una indexación/reindexación.

    El endpoint original tenía una llamada a _run_processing()
    con un único argumento aunque la función requiere document_id
    y job_id. Aquí se mantiene siempre la firma correcta.
    """

    # ---------------------------------------------------------
    # DOCUMENT
    # ---------------------------------------------------------

    document = await db.scalar(select(Document).where(Document.id == document_id))

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # ---------------------------------------------------------
    # ACCESS
    # ---------------------------------------------------------

    await _validate_kb_access(
        db,
        document.knowledge_base_id,
        current_user,
    )

    # ---------------------------------------------------------
    # CHECK ACTIVE JOB
    # ---------------------------------------------------------

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
            "processing_status": (active_job.status or "").lower(),
            "message": "Document indexing already running",
        }

    # ---------------------------------------------------------
    # NEW JOB
    #
    # Permite reindexar documentos ya completados o fallidos.
    # ---------------------------------------------------------

    job = ProcessingJob(
        id=uuid4(),
        tenant_id=document.tenant_id,
        document_id=document.id,
        status="PENDING",
        chunks_generated=0,
    )

    _set_if_attribute(
        job,
        "embedding_model",
        EMBEDDING_MODEL,
    )

    _set_if_attribute(
        job,
        "llm_model",
        MODEL,
    )

    _set_if_attribute(
        job,
        "started_at",
        None,
    )

    _set_if_attribute(
        job,
        "finished_at",
        None,
    )

    _set_if_attribute(
        job,
        "error_message",
        None,
    )

    db.add(job)

    await db.commit()

    # ---------------------------------------------------------
    # LAUNCH BACKGROUND JOB
    # ---------------------------------------------------------

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
        "processing_status": "pending",
        "active": False,
        "embedding_model": EMBEDDING_MODEL,
        "generation_model": MODEL,
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
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    knowledge_base_id: UUID = Form(...),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sube un documento o vídeo.

    Después de guardar correctamente el documento:

        1. crea Document
        2. crea DocumentVersion
        3. crea ProcessingJob
        4. hace COMMIT
        5. lanza _run_processing() en background

    Por tanto el cliente no necesita llamar a /index después
    de subir un archivo.
    """

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

    await _validate_kb_access(
        db,
        knowledge_base_id,
        current_user,
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

    # UploadFile.size puede no estar disponible dependiendo
    # de la versión/configuración de Starlette.
    if size == 0:
        await file.seek(0, 2)
        size = file.tell()
        await file.seek(0)

    if size == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file submitted",
        )

    mime_type = _normalise_mime_type(file.content_type)

    is_video = _is_video_file(
        file.filename,
        mime_type,
    )

    logger.info(
        "[UPLOAD] filename=%s size=%s mime=%s video=%s",
        file.filename,
        size,
        mime_type or "unknown",
        is_video,
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
    job_id = uuid4()

    try:
        document = Document(
            id=doc_id,
            tenant_id=kb.tenant_id,
            knowledge_base_id=kb.id,
            owner_id=current_user.id,
            filename=file.filename,
            title=title or file.filename,
            description=description,
            mime_type=(file.content_type or "application/octet-stream"),
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
            id=job_id,
            tenant_id=kb.tenant_id,
            document_id=doc_id,
            status="PENDING",
            chunks_generated=0,
        )

        # Guardamos desde el principio qué modelos va a utilizar
        # el pipeline.
        _set_if_attribute(
            job,
            "embedding_model",
            EMBEDDING_MODEL,
        )

        _set_if_attribute(
            job,
            "llm_model",
            MODEL,
        )

        _set_if_attribute(
            job,
            "error_message",
            None,
        )

        _set_if_attribute(
            job,
            "started_at",
            None,
        )

        _set_if_attribute(
            job,
            "finished_at",
            None,
        )

        db.add(job)

        # MUY IMPORTANTE:
        # el commit debe ocurrir antes de lanzar BackgroundTasks.
        await db.commit()

    except Exception:
        await db.rollback()

        try:
            await storage.delete(saved_path)
        except Exception:
            logger.exception("Could not delete storage file " "after DB failure")

        logger.exception("Failed to persist document records in DB")

        raise HTTPException(
            status_code=500,
            detail="Database registration failed",
        )

    # ---------------------------------------------------------
    # 8. LANZAR PROCESAMIENTO AUTOMÁTICAMENTE
    # ---------------------------------------------------------

    background_tasks.add_task(
        _run_processing,
        doc_id,
        job_id,
    )

    logger.info(
        "[UPLOAD] Document created document=%s job=%s "
        "video=%s generation_model=%s embedding_model=%s",
        doc_id,
        job_id,
        is_video,
        MODEL,
        EMBEDDING_MODEL,
    )

    # ---------------------------------------------------------
    # 9. RESPUESTA
    # ---------------------------------------------------------

    return UploadResponse(
        id=doc_id,
        message=(
            "Video uploaded successfully and processing started."
            if is_video
            else "Document uploaded successfully and processing started."
        ),
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Elimina completamente un documento de la Knowledge Base.

    Elimina:

        - ProcessingJob
        - Embedding
        - Chunk
        - DocumentVersion
        - Document
        - archivo físico

    Además reconstruye el índice BM25 del tenant.

    No permite eliminar un documento mientras está siendo
    procesado para evitar carreras con _run_processing().
    """

    print("=" * 80)
    print(f"[DELETE] INICIO document_id={document_id}")
    print("=" * 80)

    # ---------------------------------------------------------
    # 1. BUSCAR DOCUMENTO
    # ---------------------------------------------------------

    print("[DELETE] Buscando documento...")

    document = await db.scalar(select(Document).where(Document.id == document_id))

    if not document:
        print(f"[DELETE] Documento NO encontrado: {document_id}")

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    print(
        "[DELETE] Documento encontrado "
        f"id={document.id} "
        f"filename={document.filename}"
    )

    # ---------------------------------------------------------
    # 2. VALIDAR ACCESO
    # ---------------------------------------------------------

    print(
        "[DELETE] Validando acceso a Knowledge Base " f"{document.knowledge_base_id}..."
    )

    await _validate_kb_access(
        db,
        document.knowledge_base_id,
        current_user,
    )

    print("[DELETE] Acceso autorizado")

    # ---------------------------------------------------------
    # 3. COMPROBAR SI ESTÁ SIENDO PROCESADO
    # ---------------------------------------------------------

    print("[DELETE] Comprobando ProcessingJob activo...")

    active_job = await db.scalar(
        select(ProcessingJob)
        .where(
            ProcessingJob.document_id == document_id,
            ProcessingJob.status.in_(
                [
                    "PENDING",
                    "RUNNING",
                ]
            ),
        )
        .order_by(ProcessingJob.id.desc())
    )

    if active_job:
        print(
            "[DELETE] Documento actualmente en procesamiento "
            f"job={active_job.id} "
            f"status={active_job.status}"
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Document cannot be deleted while it is "
                "being processed. Wait until processing finishes."
            ),
        )

    print("[DELETE] No hay procesamiento activo")

    # ---------------------------------------------------------
    # 4. GUARDAR INFORMACIÓN NECESARIA ANTES DE BORRAR
    # ---------------------------------------------------------

    tenant_id = document.tenant_id
    storage_path = document.storage_path

    print("[DELETE] Datos guardados antes de eliminar:")

    print(f"[DELETE] tenant_id={tenant_id}")
    print(f"[DELETE] storage_path={storage_path}")

    # ---------------------------------------------------------
    # 5. STORAGE
    # ---------------------------------------------------------

    storage = StorageService()

    # ---------------------------------------------------------
    # 6. ELIMINAR DATOS DE BD
    # ---------------------------------------------------------

    try:

        # -----------------------------------------------------
        # PROCESSING JOBS
        # -----------------------------------------------------

        print("[DELETE] Eliminando ProcessingJobs...")

        jobs_result = await db.execute(
            select(ProcessingJob).where(ProcessingJob.document_id == document_id)
        )

        jobs = jobs_result.scalars().all()

        print(f"[DELETE] ProcessingJobs encontrados: {len(jobs)}")

        for job in jobs:
            await db.delete(job)

        # -----------------------------------------------------
        # CHUNKS
        # -----------------------------------------------------

        print("[DELETE] Buscando chunks...")

        chunks_result = await db.execute(
            select(Chunk).where(Chunk.document_id == document_id)
        )

        chunks = chunks_result.scalars().all()

        print(f"[DELETE] Chunks encontrados: {len(chunks)}")

        # -----------------------------------------------------
        # EMBEDDINGS
        # -----------------------------------------------------
        #
        # Los embeddings dependen de Chunk.
        #
        # Primero eliminamos embeddings.
        # -----------------------------------------------------

        chunk_ids = [chunk.id for chunk in chunks]

        if chunk_ids:

            print("[DELETE] Eliminando embeddings " f"de {len(chunk_ids)} chunks...")

            embeddings_result = await db.execute(
                select(Embedding).where(Embedding.chunk_id.in_(chunk_ids))
            )

            embeddings = embeddings_result.scalars().all()

            print("[DELETE] Embeddings encontrados: " f"{len(embeddings)}")

            for embedding in embeddings:
                await db.delete(embedding)

        # -----------------------------------------------------
        # CHUNKS
        # -----------------------------------------------------

        print("[DELETE] Eliminando chunks...")

        for chunk in chunks:
            await db.delete(chunk)

        # -----------------------------------------------------
        # DOCUMENT VERSIONS
        # -----------------------------------------------------

        print("[DELETE] Eliminando DocumentVersions...")

        versions_result = await db.execute(
            select(DocumentVersion).where(DocumentVersion.document_id == document_id)
        )

        versions = versions_result.scalars().all()

        print("[DELETE] DocumentVersions encontrados: " f"{len(versions)}")

        for version in versions:
            await db.delete(version)

        # -----------------------------------------------------
        # DOCUMENT
        # -----------------------------------------------------

        print("[DELETE] Eliminando Document...")

        await db.delete(document)

        # -----------------------------------------------------
        # COMMIT
        # -----------------------------------------------------

        print("[DELETE] Haciendo COMMIT...")

        await db.commit()

        print(
            f"[DELETE] Base de datos actualizada "
            f"correctamente document={document_id}"
        )

    except Exception as exc:

        print("=" * 80)
        print("[DELETE] ERROR durante eliminación BD")
        print(f"[DELETE] document_id={document_id}")
        print(f"[DELETE] error={exc}")
        print("=" * 80)

        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete document",
        )

    # ---------------------------------------------------------
    # 7. ELIMINAR ARCHIVO FÍSICO
    # ---------------------------------------------------------

    if storage_path:

        print("[DELETE] Eliminando archivo físico:")
        print(f"[DELETE] {storage_path}")

        try:

            await storage.delete(storage_path)

            print("[DELETE] Archivo físico eliminado")

        except Exception as exc:

            # IMPORTANTE:
            #
            # La BD ya está eliminada.
            # No debemos devolver 500 porque provocaría
            # confusión al cliente.
            #
            # El documento ya no existe lógicamente.

            print("[DELETE] WARNING: " "no se pudo eliminar archivo físico")

            print(f"[DELETE] error={exc}")

    # ---------------------------------------------------------
    # 8. RECONSTRUIR BM25
    # ---------------------------------------------------------

    print("[DELETE] Reconstruyendo índice BM25 " f"tenant={tenant_id}...")

    try:

        # Creamos un servicio con la sesión actual.
        ingest_service = IngestService(db)

        await ingest_service._rebuild_bm25_index(str(tenant_id))

        print("[DELETE] BM25 reconstruido correctamente")

    except Exception as exc:

        print("[DELETE] WARNING: " "no se pudo reconstruir BM25")

        print(f"[DELETE] error={exc}")

    # ---------------------------------------------------------
    # 9. FIN
    # ---------------------------------------------------------

    print("=" * 80)
    print(f"[DELETE] COMPLETADO document_id={document_id}")
    print("=" * 80)

    return None


# ============================================================
# PROGRESS / SSE
# ============================================================


@router.get("/{document_id}/progress")
async def get_document_progress(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stream SSE del estado de procesamiento.

    Ejemplo:

        data: {
            "document_id": "...",
            "job_id": "...",
            "status": "RUNNING",
            "processing_status": "running",
            "active": false,
            "step": "indexing",
            "chunks": 12,
            "embedding_model": "qwen3-embedding:latest",
            "generation_model": "llama3",
            "error": null
        }
    """

    # --------------------------------------------------------
    # DOCUMENT
    # --------------------------------------------------------

    document = await db.scalar(select(Document).where(Document.id == document_id))

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # --------------------------------------------------------
    # AUTHORIZATION
    # --------------------------------------------------------

    await _validate_kb_access(
        db,
        document.knowledge_base_id,
        current_user,
    )

    # --------------------------------------------------------
    # SSE
    # --------------------------------------------------------

    async def event_generator():
        last_status = None
        last_chunks = None
        last_error = None

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
                    "processing_status": "uploaded",
                    "active": False,
                    "step": "upload",
                    "detail": ("Documento subido. " "Pendiente de indexación."),
                    "chunks": 0,
                    "embedding_model": EMBEDDING_MODEL,
                    "generation_model": MODEL,
                    "error": None,
                }

                yield (
                    "data: "
                    + json.dumps(
                        payload,
                        ensure_ascii=False,
                        default=str,
                    )
                    + "\n\n"
                )

                await asyncio.sleep(2)
                continue

            # ------------------------------------------------
            # Status
            # ------------------------------------------------

            status_value = (job.status or "UNKNOWN").upper()

            chunks = job.chunks_generated or 0

            error = _job_error(job)

            # ------------------------------------------------
            # Solo enviar cambios
            # ------------------------------------------------

            if (
                status_value != last_status
                or chunks != last_chunks
                or error != last_error
            ):
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
                    detail = f"Estado: {status_value}"

                payload = {
                    "document_id": str(document_id),
                    "job_id": str(job.id),
                    "status": status_value,
                    "processing_status": (status_value.lower()),
                    "active": (status_value == "COMPLETED"),
                    "step": step,
                    "detail": detail,
                    "chunks": chunks,
                    "embedding_model": (
                        getattr(
                            job,
                            "embedding_model",
                            None,
                        )
                        or EMBEDDING_MODEL
                    ),
                    "generation_model": (
                        getattr(
                            job,
                            "llm_model",
                            None,
                        )
                        or MODEL
                    ),
                    "error": error,
                }

                yield (
                    "data: "
                    + json.dumps(
                        payload,
                        ensure_ascii=False,
                        default=str,
                    )
                    + "\n\n"
                )

                last_status = status_value
                last_chunks = chunks
                last_error = error

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
