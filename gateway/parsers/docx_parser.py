from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from docling.document_converter import DocumentConverter

from .base import FileParser, ParsingContext
from .parsed_document import ParsedDocument

logger = logging.getLogger(__name__)


class DocxParser(FileParser):

    def __init__(self) -> None:
        self.converter = DocumentConverter()

    async def parse(
        self,
        file: Path,
        context: ParsingContext,
    ) -> ParsedDocument:
        if not file.exists():
            raise FileNotFoundError(f"File not found: {file}")

        if not file.is_file():
            raise ValueError(f"{file} is not a valid file")

        logger.info("Parsing DOCX %s", file)

        loop = asyncio.get_running_loop()
        markdown = await loop.run_in_executor(None, self._convert, file)
        checksum = hashlib.sha256(file.read_bytes()).hexdigest()

        return ParsedDocument(
            filename=file.name,
            extension=file.suffix.lower(),
            title=file.stem,
            markdown=markdown,
            language=context.language or "es",
            word_count=len(markdown.split()),
            character_count=len(markdown),
            metadata={
                "source": str(file),
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "parser": "docling",
                "size": file.stat().st_size,
                "checksum": checksum,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "tenant_id": str(context.tenant_id),
                "organization_id": str(context.organization_id) if context.organization_id else None,
                "department_id": str(context.department_id) if context.department_id else None,
                "member_id": str(context.member_id) if context.member_id else None,
                "uploaded_by": str(context.uploaded_by) if context.uploaded_by else None,
                "tags": context.tags,
            },
        )

    def _convert(self, file: Path) -> str:
        result = self.converter.convert(file)
        return result.document.export_to_markdown()