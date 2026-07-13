from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from docling.document_converter import DocumentConverter

from .base import FileParser
from .parsed_document import ParsedDocument

logger = logging.getLogger(__name__)


class DocxParser(FileParser):

    def __init__(self):

        self.converter = DocumentConverter()

    async def parse(
        self,
        file: Path,
    ) -> ParsedDocument:

        if not file.exists():
            raise FileNotFoundError(file)

        logger.info("Parsing DOCX %s", file)

        loop = asyncio.get_running_loop()

        markdown = await loop.run_in_executor(
            None,
            self._convert,
            file,
        )

        return ParsedDocument(
            filename=file.name,
            extension=file.suffix.lower(),
            markdown=markdown,
            metadata={
                "source": str(file),
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "parser": "docling",
            },
        )

    def _convert(
        self,
        file: Path,
    ) -> str:

        result = self.converter.convert(file)

        return result.document.export_to_markdown()