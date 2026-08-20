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

DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


class DocxParser(FileParser):
    """Parser DOCX basado en Docling."""

    def __init__(self) -> None:
        self.converter = DocumentConverter()

    async def parse(
        self,
        file: Path,
        context: ParsingContext | None = None,
    ) -> ParsedDocument:
        if not file.exists():
            raise FileNotFoundError(file)

        if not file.is_file():
            raise ValueError(f"{file} is not a valid file")

        logger.info("Parsing DOCX %s", file)

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self.converter.convert, file)
        markdown = result.document.export_to_markdown().strip()

        checksum = hashlib.sha256(file.read_bytes()).hexdigest()
        language = (
            context.language
            if context and context.language
            else "es"
        )

        metadata: dict = {
            "source": str(file),
            "mime_type": DOCX_MIME,
            "parser": "docling",
            "size": file.stat().st_size,
            "checksum": checksum,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if context is not None:
            metadata.update(
                {
                    "tenant_id": str(context.tenant_id),
                    "organization_id": (
                        str(context.organization_id)
                        if context.organization_id
                        else None
                    ),
                    "department_id": (
                        str(context.department_id)
                        if context.department_id
                        else None
                    ),
                    "member_id": (
                        str(context.member_id) if context.member_id else None
                    ),
                    "uploaded_by": (
                        str(context.uploaded_by)
                        if context.uploaded_by
                        else None
                    ),
                    "tags": context.tags,
                }
            )

        return ParsedDocument(
            filename=file.name,
            extension=file.suffix.lower(),
            title=file.stem,
            markdown=markdown,
            language=language,
            word_count=len(markdown.split()),
            character_count=len(markdown),
            metadata=metadata,
        )
