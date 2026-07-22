import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import Document
from models.processing_job import ProcessingJob

from services.ingest_service import IngestService

logger = logging.getLogger(__name__)


class DocumentProcessor:

    def __init__(self, session: AsyncSession):
        self.session = session
        self.ingest = IngestService(session)

    async def process(self, document_id: UUID):

        logger.info(
            "Processing document %s",
            document_id,
        )

        document = await self.session.scalar(
            select(Document).where(
                Document.id == document_id
            )
        )

        if document is None:
            raise ValueError(
                f"Document {document_id} not found"
            )

        job = await self.session.scalar(
            select(ProcessingJob).where(
                ProcessingJob.document_id == document_id
            )
        )

        try:

            if job:
                job.status = "PROCESSING"
                job.started_at = datetime.now()
                await self.session.commit()
            chunks_generated = await self.ingest.process(
                document
            )
            if job:
                job.status = "COMPLETED"
                job.finished_at = datetime.now()
                job.chunks_generated = chunks_generated
                await self.session.commit()
            logger.info(
                "Document %s processed successfully",
                document.filename,
            )
            return chunks_generated

        except Exception as e:
            logger.exception(
                "Pipeline failed"
            )
            await self.session.rollback()

            if job:
                job.status = "FAILED"
                job.finished_at = datetime.now()
                job.error_message = str(e)
                await self.session.commit()
            raise