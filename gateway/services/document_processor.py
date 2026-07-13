import logging
import time
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from parsers.factory import FileParserFactory

from models.document import Document
from models.processing_job import ProcessingJob

from services.chunking_service import ChunkingService
from services.embedding_service import EmbeddingService
from services.knowledge_graph_service import KnowledgeGraphService
from services.vectore_store import VectorStore

logger = logging.getLogger(__name__)


class DocumentProcessor:

    def __init__(self, session: AsyncSession):

        self.session = session

        self.parser_factory = FileParserFactory()
        self.chunker = ChunkingService()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.graph_service = KnowledgeGraphService()

    async def process(self, document_id: UUID):

        print("=" * 80)
        print("INICIO DEL PIPELINE")
        print(document_id)
        print("=" * 80)

        document = await self.session.scalar(
            select(Document).where(Document.id == document_id)
        )

        if document is None:
            print("Documento no encontrado")
            return

        print(f"Documento: {document.filename}")
        print(f"Ruta: {document.storage_path}")

        job = await self.session.scalar(
            select(ProcessingJob).where(
                ProcessingJob.document_id == document_id
            )
        )

        try:

            if job:
                job.status = "PROCESSING"
                job.started_at = datetime.utcnow()
                await self.session.commit()

            ##################################################################
            # PARSER
            ##################################################################

            print("\n[1/5] Parseando PDF...")

            t0 = time.time()

            parser = self.parser_factory.create(
                Path(document.storage_path)
            )

            parsed_document = await parser.parse(
                Path(document.storage_path)
            )

            print("Parser terminado")

            print(
                "Markdown:",
                len(parsed_document.markdown),
                "caracteres"
            )

            print(
                parsed_document.markdown[:500]
            )

            print(
                f"Tiempo parser: {time.time()-t0:.2f}s"
            )

            ##################################################################
            # CHUNKING
            ##################################################################

            print("\n[2/5] Creando chunks...")

            t0 = time.time()

            chunks = await self.chunker.create_chunks(
                parsed_document
            )

            print(
                "Chunks generados:",
                len(chunks)
            )

            if chunks:

                print("\nPrimer chunk\n")

                print(chunks[0].page_content[:800])

            print(
                f"Tiempo chunking: {time.time()-t0:.2f}s"
            )

            ##################################################################
            # EMBEDDINGS
            ##################################################################

            print("\n[3/5] Generando embeddings...")

            t0 = time.time()

            embedded_chunks = await self.embedding_service.create_embeddings(
                chunks
            )

            print(
                "Embeddings:",
                len(embedded_chunks)
            )

            print(
                f"Tiempo embeddings: {time.time()-t0:.2f}s"
            )

            ##################################################################
            # CHROMA
            ##################################################################

            print("\n[4/5] Guardando en Chroma...")

            t0 = time.time()

            self.vector_store.add_embedded_chunks(

                collection_name=str(document.knowledge_base_id),

                embedded_chunks=embedded_chunks,

                base_metadata={

                    "tenant_id": str(document.tenant_id),

                    "knowledge_base_id": str(document.knowledge_base_id),

                    "document_id": str(document.id),

                    "source": document.filename,

                },

            )

            print("Embeddings almacenados")

            print(
                f"Tiempo Chroma: {time.time()-t0:.2f}s"
            )

            ##################################################################
            # KNOWLEDGE GRAPH
            ##################################################################

            print("\n[5/5] Construyendo Knowledge Graph...")

            t0 = time.time()

            await self.graph_service.build(

                tenant_id=document.tenant_id,

                knowledge_base_id=document.knowledge_base_id,

                document=document,

                parsed_document=parsed_document,

                chunks=chunks,

            )

            print("Knowledge Graph generado")

            print(
                f"Tiempo grafo: {time.time()-t0:.2f}s"
            )

            ##################################################################

            if job:

                job.status = "COMPLETED"

                job.finished_at = datetime.utcnow()

                job.chunks_generated = len(chunks)

                await self.session.commit()

            print("\nPIPELINE FINALIZADO CORRECTAMENTE")

        except Exception as exc:

            print("\nERROR EN EL PIPELINE")
            print(type(exc).__name__)
            print(exc)

            logger.exception(exc)

            await self.session.rollback()

            if job:

                job.status = "FAILED"

                job.finished_at = datetime.utcnow()

                job.error_message = str(exc)

                await self.session.commit()

            raise