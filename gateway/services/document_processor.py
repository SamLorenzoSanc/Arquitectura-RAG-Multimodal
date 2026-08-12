import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import Document
from models.processing_job import ProcessingJob
from services.ingest_service import IngestService

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self, session: AsyncSession):
        self.session = session
        # Delegamos la lógica de LlamaParse y pgvector al servicio de ingesta
        self.ingest = IngestService(session)

    async def process(self, document_id: UUID):
        logger.info("Processing document %s", document_id)

        document = await self.session.scalar(
            select(Document).where(Document.id == document_id)
        )

        if not document:
            raise ValueError(f"Document {document_id} not found")

        job = await self.session.scalar(
            select(ProcessingJob).where(ProcessingJob.document_id == document_id)
        )

        try:
            if job:
                job.status = "PROCESSING"
                # Usar siempre UTC para consistencia en la BD
                job.started_at = datetime.now(timezone.utc)
                await self.session.commit()

            # --- Aquí ocurre la magia pesada ---
            chunks_generated = await self.ingest.process(document)
            # -----------------------------------

            if job:
                job.status = "COMPLETED"
                job.finished_at = datetime.now(timezone.utc)
                job.chunks_generated = chunks_generated
                await self.session.commit()

            logger.info("Document %s processed successfully", document.filename)
            return chunks_generated

        except Exception as e:
            logger.exception("Pipeline failed for document %s", document_id)

            # 1. Revertimos cualquier inserción a medias (chunks, embeddings incompletos)
            await self.session.rollback()

            # 2. Actualizamos el estado usando SQL directo (update)
            # Esto evita errores de objetos "caducados" tras el rollback.
            if job:
                await self.session.execute(
                    update(ProcessingJob)
                    .where(ProcessingJob.id == job.id)
                    .values(
                        status="FAILED",
                        finished_at=datetime.now(timezone.utc),
                        # Truncamos el error por seguridad (ej. max 500 caracteres)
                        error_message=str(e)[:500],
                    )
                )
                await self.session.commit()

            raise
