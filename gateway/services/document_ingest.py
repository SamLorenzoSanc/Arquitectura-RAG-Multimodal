"""Ingesta asíncrona: fragmenta, embebe y publica progreso."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import text

from services.database import AsyncSessionLocal
from services.embedding_reindex import record_reindex_on_job, reindex_embeddings
from services.embedding_indexer import enqueue_document, mark_indexed_for_runtime
from services.ingest_progress import set_progress
from services.rag_service import DEFAULT_EMBEDDING_MODEL, RAGService

logger = logging.getLogger(__name__)


async def ingest_uploaded_document(
    document_id: str,
    tenant_id: str,
    knowledge_base_id: str,
    force_rebuild: bool = False,
) -> None:
    set_progress(
        document_id,
        stage="extract",
        percent=18,
        message="Extrayendo texto del documento…",
        status="running",
        chunks=0,
        embedded=0,
        total=0,
        error=None,
    )
    async with AsyncSessionLocal() as db:
        try:
            await db.execute(
                text(
                    """
                    UPDATE processing_jobs
                    SET status = 'running', started_at = COALESCE(started_at, NOW())
                    WHERE document_id = :document_id
                    """
                ),
                {"document_id": document_id},
            )
            await db.commit()

            try:
                file_hash_row = await db.execute(
                    text("SELECT file_hash FROM documents WHERE id = :id"),
                    {"id": document_id},
                )
                file_hash = file_hash_row.scalar()
                await enqueue_document(
                    db,
                    document_id=document_id,
                    source_hash=str(file_hash) if file_hash else None,
                    force=force_rebuild,
                )
                await db.commit()
            except Exception:
                logger.exception("No se pudo encolar el indexador de embeddings")

            async def on_progress(event: dict) -> None:
                set_progress(document_id, status="running", error=None, **event)

            result = await reindex_embeddings(
                db,
                tenant_id=tenant_id,
                models=[DEFAULT_EMBEDDING_MODEL],
                knowledge_base_id=knowledge_base_id,
                document_id=document_id,
                on_progress=on_progress,
                force_rebuild=force_rebuild,
            )
            await record_reindex_on_job(
                db,
                document_id=document_id,
                tenant_id=tenant_id,
                models=[DEFAULT_EMBEDDING_MODEL],
                result=result,
            )
            try:
                file_hash_row = await db.execute(
                    text("SELECT file_hash FROM documents WHERE id = :id"),
                    {"id": document_id},
                )
                file_hash = file_hash_row.scalar()
                await mark_indexed_for_runtime(
                    db,
                    document_id=document_id,
                    runtime_model_id=DEFAULT_EMBEDDING_MODEL,
                    source_hash=str(file_hash) if file_hash else None,
                )
                await db.commit()
            except Exception:
                logger.exception("No se pudo marcar el modelo por defecto como indexado")
            try:
                from rag.composition import build_rag_container

                await build_rag_container().ingest.execute(str(tenant_id))
            except Exception:
                logger.exception("Post-ingesta del catálogo falló")
            try:
                RAGService.invalidate_retrieval_cache(str(tenant_id))
            except Exception:
                logger.exception("No se pudo invalidar la caché de recuperación")
            indexed = int(result.get("chunks") or 0)
            set_progress(
                document_id,
                stage="done",
                percent=100,
                status="completed",
                chunks=indexed,
                total=indexed,
                embedded=indexed,
                message=f"{indexed} fragmentos indexados.",
                error=None,
            )
        except Exception as exc:
            logger.exception("Ingesta fallida para %s", document_id)
            message = str(exc)[:2000]
            set_progress(
                document_id,
                stage="error",
                percent=100,
                status="failed",
                error=message,
                message=message,
            )
            try:
                await db.execute(
                    text(
                        """
                        UPDATE processing_jobs
                        SET
                            status = 'failed',
                            error_message = :error,
                            finished_at = :finished_at
                        WHERE document_id = :document_id
                        """
                    ),
                    {
                        "document_id": document_id,
                        "error": message,
                        "finished_at": datetime.now(timezone.utc),
                    },
                )
                await db.commit()
            except Exception:
                logger.exception("No se pudo marcar el job como fallido")
