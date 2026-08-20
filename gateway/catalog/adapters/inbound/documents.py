"""Consulta e ingesta documental local del monolito."""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Document,
    KnowledgeBase,
    OrganizationMember,
    ProcessingJob,
    Tenant,
    User,
)
from models.chunk import Chunk
from routes.auth import get_current_user
from services.database import get_db
from storage.local import LocalFileStorage
from services.evaluation_dataset import safe_rollback
from services.embedding_reindex import (
    EMBEDDING_CATALOG,
    ensure_multi_embedding_schema,
    list_indexed_models,
    record_reindex_on_job,
    reindex_embeddings,
)
from services.ingest_progress import get_progress, set_progress
from services.rag_service import DEFAULT_EMBEDDING_MODEL, RAGService
from services.video_extract import MAX_UPLOAD_BYTES

router = APIRouter(prefix="/documents", tags=["Documents"])
lab_router = APIRouter(prefix="/documents", tags=["Documents lab"])
_storage = LocalFileStorage()
logger = logging.getLogger(__name__)


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

    ids = [document.id for document in documents]
    chunk_map: dict[str, int] = {}
    model_map: dict[str, list[str]] = {}
    if ids:
        try:
            count_rows = await db.execute(
                text(
                    """
                    SELECT document_id::text AS document_id, COUNT(*)::int AS n
                    FROM chunks
                    WHERE document_id IN :ids
                    GROUP BY document_id
                    """
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": ids},
            )
            chunk_map = {
                str(row.document_id): int(row.n) for row in count_rows
            }
            model_rows = await db.execute(
                text(
                    """
                    SELECT c.document_id::text AS document_id, e.model
                    FROM embeddings e
                    JOIN chunks c ON c.id = e.chunk_id
                    WHERE c.document_id IN :ids
                    GROUP BY c.document_id, e.model
                    ORDER BY e.model
                    """
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": ids},
            )
            for row in model_rows:
                model_map.setdefault(str(row.document_id), []).append(str(row.model))
        except Exception:
            await safe_rollback(db)

    response = []
    for document in documents:
        job = await db.scalar(
            select(ProcessingJob)
            .where(ProcessingJob.document_id == document.id)
            .order_by(ProcessingJob.started_at.desc().nulls_last())
        )
        doc_key = str(document.id)
        chunk_count = chunk_map.get(
            doc_key, getattr(job, "chunks_generated", 0) if job else 0
        ) or 0
        indexed_models = model_map.get(doc_key) or []
        embedding_model = ", ".join(indexed_models) or (
            getattr(job, "embedding_model", None) if job else None
        )
        processing_status = (job.status or "uploaded").lower() if job else "uploaded"
        if indexed_models:
            processing_status = "completed"
        updated_at = (
            getattr(job, "finished_at", None)
            or getattr(job, "started_at", None)
            or document.uploaded_at
        )
        progress = get_progress(doc_key)
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
                "chunks": chunk_count,
                "attempts": getattr(job, "attempts", 0) if job else 0,
                "embedding_model": embedding_model,
                "generation_model": getattr(job, "llm_model", None) if job else None,
                "llm_model": getattr(job, "llm_model", None) if job else None,
                "error": getattr(job, "error_message", None) if job else None,
                "progress": progress,
            }
        )

    return response


@router.post("")
async def upload_document(
    knowledge_base_id: UUID = Form(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ingesta local: guarda el fichero, fragmenta el texto y genera embeddings."""
    await _validate_kb_access(db, knowledge_base_id, current_user)
    kb = await db.scalar(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)
    )
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")
    try:
        tenant_id = UUID(str(kb.tenant_id))
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Knowledge Base not found") from exc

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="El archivo supera 100 MiB. Comprime el vídeo o recórtalo.",
        )

    save_error: str | None = None
    try:
        storage_path = await _storage.save_bytes(
            content, file.filename, tenant_id, knowledge_base_id
        )
    except Exception as exc:
        save_error = str(exc)[:2000]
        storage_path = f"failed://{file.filename or 'documento'}"

    try:
        owner_id = UUID(str(current_user.id))
    except (TypeError, ValueError):
        owner_id = None

    document = Document(
        id=uuid4(),
        filename=file.filename or "documento.pdf",
        title=title or file.filename,
        description=description,
        storage_path=storage_path,
        size=len(content),
        mime_type=file.content_type,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
        owner_id=owner_id,
        file_hash=hashlib.sha256(content).hexdigest(),
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(document)
    await db.flush()

    job = ProcessingJob(
        id=uuid4(),
        document_id=document.id,
        tenant_id=tenant_id,
        status="failed" if save_error else "running",
        chunks_generated=0,
        embedding_model=None,
        llm_model=None,
        started_at=datetime.now(timezone.utc),
        error_message=save_error,
        finished_at=datetime.now(timezone.utc) if save_error else None,
    )
    db.add(job)
    # El documento entra en la tabla de inmediato, aunque el procesado falle después.
    await db.commit()
    await db.refresh(job)
    logger.info(
        "Documento persistido id=%s kb=%s tenant=%s path=%s",
        document.id,
        knowledge_base_id,
        tenant_id,
        storage_path,
    )

    if save_error:
        set_progress(
            str(document.id),
            stage="error",
            percent=100,
            status="failed",
            error=save_error,
            message=save_error,
        )
        return {
            "status": "error",
            "id": str(document.id),
            "filename": document.filename,
            "storage_path": storage_path,
            "processing_status": "failed",
            "chunks": 0,
            "embedding_model": None,
            "error": save_error,
            "message": f"Error al procesar el documento: {save_error}",
        }

    set_progress(
        str(document.id),
        stage="queued",
        percent=15,
        status="running",
        message="Archivo guardado. Iniciando indexación…",
        chunks=0,
        embedded=0,
        total=0,
        error=None,
    )
    _queue_ingest(
        str(document.id),
        str(tenant_id),
        str(knowledge_base_id),
    )
    return {
        "status": "accepted",
        "id": str(document.id),
        "filename": document.filename,
        "storage_path": storage_path,
        "processing_status": "running",
        "chunks": 0,
        "embedding_model": None,
        "error": None,
        "message": "Documento recibido. Indexando fragmentos y embeddings.",
        "progress": get_progress(str(document.id)),
    }


def _queue_ingest(
    document_id: str,
    tenant_id: str,
    knowledge_base_id: str,
    *,
    force_rebuild: bool = False,
) -> None:
    def _log_ingest(task: asyncio.Task) -> None:
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            return
        except Exception:
            return
        if exc:
            logger.exception("Ingesta en segundo plano falló", exc_info=exc)

    from services.document_ingest import ingest_uploaded_document

    task = asyncio.create_task(
        ingest_uploaded_document(
            document_id,
            tenant_id,
            knowledge_base_id,
            force_rebuild=force_rebuild,
        ),
        name=f"ingest-{document_id}",
    )
    task.add_done_callback(_log_ingest)


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: UUID,
    knowledge_base_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Vuelve a extraer texto (OCR si hace falta) y regenera fragmentos y embeddings."""
    await _validate_kb_access(db, knowledge_base_id, current_user)
    document = await db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.knowledge_base_id == knowledge_base_id,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if not document.storage_path or str(document.storage_path).startswith("failed://"):
        raise HTTPException(
            status_code=409,
            detail="El documento no tiene un fichero almacenado para reprocesar.",
        )

    set_progress(
        str(document.id),
        stage="queued",
        percent=10,
        status="running",
        message="Reprocesando documento con extracción OCR…",
        chunks=0,
        embedded=0,
        total=0,
        error=None,
    )
    await db.execute(
        text(
            """
            UPDATE processing_jobs
            SET status = 'running', started_at = COALESCE(started_at, NOW()),
                error_message = NULL, finished_at = NULL
            WHERE document_id = :document_id
            """
        ),
        {"document_id": str(document.id)},
    )
    await db.commit()
    _queue_ingest(
        str(document.id),
        str(document.tenant_id),
        str(knowledge_base_id),
        force_rebuild=True,
    )
    return {
        "status": "accepted",
        "id": str(document.id),
        "processing_status": "running",
        "message": "Reprocesando el documento. El OCR solo se aplica a páginas ilegibles.",
        "progress": get_progress(str(document.id)),
    }


@router.get("/{document_id}/progress")
async def document_progress(
    document_id: UUID,
    knowledge_base_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _validate_kb_access(db, knowledge_base_id, current_user)
    document = await db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.knowledge_base_id == knowledge_base_id,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    live = get_progress(str(document_id))
    if live:
        return live

    job = await db.scalar(
        select(ProcessingJob)
        .where(ProcessingJob.document_id == document_id)
        .order_by(ProcessingJob.started_at.desc().nulls_last())
    )
    chunks = 0
    embedded = 0
    try:
        chunks = int(
            await db.scalar(
                text("SELECT COUNT(*) FROM chunks WHERE document_id = :document_id"),
                {"document_id": document_id},
            )
            or 0
        )
        embedded = int(
            await db.scalar(
                text(
                    """
                    SELECT COUNT(*) FROM embeddings e
                    JOIN chunks c ON c.id = e.chunk_id
                    WHERE c.document_id = :document_id
                    """
                ),
                {"document_id": document_id},
            )
            or 0
        )
    except Exception:
        await safe_rollback(db)

    status = (job.status or "running").lower() if job else "running"
    if status == "completed":
        percent = 100
        stage = "done"
        message = f"{chunks} fragmentos indexados."
    elif status == "failed":
        percent = 100
        stage = "error"
        message = job.error_message if job else "Error al indexar."
    elif chunks and embedded:
        percent = 40 + int(55 * (embedded / max(chunks, 1)))
        stage = "embed"
        message = f"Embeddings {embedded}/{chunks}…"
    elif chunks:
        percent = 38
        stage = "chunk"
        message = f"{chunks} fragmentos listos."
    else:
        percent = 20
        stage = "extract"
        message = "Extrayendo texto del documento…"

    return {
        "document_id": str(document_id),
        "stage": stage,
        "percent": percent,
        "status": status,
        "message": message,
        "chunks": chunks,
        "embedded": embedded,
        "total": chunks,
        "error": getattr(job, "error_message", None) if job else None,
    }


def _chunk_overlap(previous: str, current: str) -> int:
    if not previous or not current:
        return 0
    limit = min(len(previous), len(current), 400)
    for size in range(limit, 19, -1):
        if previous.endswith(current[:size]):
            return size
    return 0


@router.get("/{document_id}/chunks")
async def list_document_chunks(
    document_id: UUID,
    knowledge_base_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve los fragmentos indexados para auditar el corte del documento."""
    document = await db.scalar(select(Document).where(Document.id == document_id))
    if document is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    kb_id = knowledge_base_id or document.knowledge_base_id
    await _validate_kb_access(db, kb_id, current_user)
    if str(document.knowledge_base_id) != str(kb_id):
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    chunks = (
        await db.scalars(
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.position.asc())
        )
    ).all()

    models_by_chunk: dict[str, list[str]] = {}
    if chunks:
        try:
            rows = await db.execute(
                text(
                    """
                    SELECT chunk_id::text AS chunk_id, model
                    FROM embeddings
                    WHERE chunk_id IN :ids
                    ORDER BY model
                    """
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": [chunk.id for chunk in chunks]},
            )
            for row in rows:
                models_by_chunk.setdefault(str(row.chunk_id), []).append(str(row.model))
        except Exception:
            await safe_rollback(db)

    payload = []
    previous = ""
    for chunk in chunks:
        content = chunk.content or ""
        overlap = _chunk_overlap(previous, content)
        payload.append(
            {
                "id": str(chunk.id),
                "position": chunk.position,
                "headline": chunk.headline or "",
                "summary": chunk.summary or "",
                "content": content,
                "char_count": len(content),
                "overlap_prev": overlap,
                "embedding_models": models_by_chunk.get(str(chunk.id), []),
            }
        )
        previous = content

    return {
        "id": str(document.id),
        "filename": document.filename,
        "title": document.title or document.filename,
        "mime_type": document.mime_type,
        "size": document.size,
        "knowledge_base_id": str(document.knowledge_base_id),
        "chunk_count": len(payload),
        "chunks": payload,
    }


class ReindexEmbeddingsRequest(BaseModel):
    knowledge_base_id: UUID
    document_id: UUID | None = None
    embedding_models: list[str] = Field(
        default_factory=lambda: [DEFAULT_EMBEDDING_MODEL]
    )


@lab_router.get("/embedding-models")
async def list_document_embedding_models(
    knowledge_base_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _validate_kb_access(db, knowledge_base_id, current_user)
    indexed: list[str] = []
    try:
        await ensure_multi_embedding_schema(db)
        indexed = await list_indexed_models(db)
    except Exception:
        await safe_rollback(db)
    return {
        "indexed": indexed,
        "default": indexed[0] if indexed else DEFAULT_EMBEDDING_MODEL,
        "catalog": EMBEDDING_CATALOG,
        "note": (
            "Reindexar con varios modelos deja un vector por chunk y modelo. "
            "Después se puede comparar cuál mejora Recall/MRR frente al otro."
        ),
    }


@lab_router.post("/reindex-embeddings")
async def reindex_document_embeddings(
    request: ReindexEmbeddingsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _validate_kb_access(db, request.knowledge_base_id, current_user)
    kb = await db.scalar(
        select(KnowledgeBase).where(KnowledgeBase.id == request.knowledge_base_id)
    )
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")
    try:
        result = await reindex_embeddings(
            db,
            tenant_id=str(kb.tenant_id),
            models=request.embedding_models,
            knowledge_base_id=str(request.knowledge_base_id),
            document_id=str(request.document_id) if request.document_id else None,
        )
        if request.document_id:
            await record_reindex_on_job(
                db,
                document_id=str(request.document_id),
                tenant_id=str(kb.tenant_id),
                models=request.embedding_models,
                result=result,
            )
        RAGService.invalidate_retrieval_cache(str(kb.tenant_id))
    except Exception as exc:
        await safe_rollback(db)
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo reindexar: {exc}",
        ) from exc
    return result


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    knowledge_base_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _validate_kb_access(db, knowledge_base_id, current_user)
    document = await db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.knowledge_base_id == knowledge_base_id,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    storage_path = document.storage_path
    tenant_id = str(document.tenant_id) if document.tenant_id else None
    await db.execute(
        text("DELETE FROM message_sources WHERE document_id = :document_id"),
        {"document_id": document_id},
    )
    await db.execute(
        text("""
            DELETE FROM embeddings
            WHERE chunk_id IN (SELECT id FROM chunks WHERE document_id = :document_id)
            """),
        {"document_id": document_id},
    )
    await db.execute(
        text("DELETE FROM chunks WHERE document_id = :document_id"),
        {"document_id": document_id},
    )
    await db.execute(
        text("DELETE FROM processing_jobs WHERE document_id = :document_id"),
        {"document_id": document_id},
    )
    await db.execute(
        text("DELETE FROM document_questions WHERE document_id = :document_id"),
        {"document_id": str(document_id)},
    )
    await db.execute(
        text("DELETE FROM rag_human_reviews WHERE document_id = :document_id"),
        {"document_id": str(document_id)},
    )
    await db.delete(document)
    await db.commit()
    if storage_path and not str(storage_path).startswith("failed://"):
        try:
            await _storage.delete(storage_path)
        except Exception:
            pass
    if tenant_id:
        RAGService.invalidate_retrieval_cache(tenant_id)
    return {"status": "deleted", "id": str(document_id)}
