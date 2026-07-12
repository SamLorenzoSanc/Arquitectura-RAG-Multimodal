from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from parsers.factory import FileParserFactory

from schemas.document import Document
from schemas.processing_job import ProcessingJob

logger = logging.getLogger(__name__)

class DocumentProcessor:

    def __init__(
        self,
        parser_factory,
        markdown_service,
        chunker,
        embedding_service,
        graph_service,
    ):

        self.parser_factory = parser_factory
        self.markdown_service = markdown_service
        self.chunker = chunker
        self.embedding_service = embedding_service
        self.graph_service = graph_service
    
    async def process(self, document: Document):

        parser = self.parser_factory.create(
            Path(document.storage_path)
        )

        parsed = await parser.parse(
            Path(document.storage_path)
        )

        markdown = self.markdown_service.clean(
            parsed.markdown
        )

        chunks = self.chunker.chunk(
            markdown
        )

        embeddings = await self.embedding_service.embed(
            chunks
        )

        await self.graph_service.ingest(
            chunks
        )