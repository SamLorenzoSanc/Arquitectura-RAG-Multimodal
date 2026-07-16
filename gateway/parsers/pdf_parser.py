from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from .base import FileParser, ParsingContext
from .parsed_document import ParsedDocument

logger = logging.getLogger(__name__)


class PdfParser(FileParser):

    def __init__(self) -> None:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True

        pdf_options = PdfFormatOption(
            pipeline_options=pipeline_options,
            backend=PyPdfiumDocumentBackend,
        )

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: pdf_options,
            }
        )

    async def parse(
        self,
        file: Path,
        context: ParsingContext,
    ) -> ParsedDocument:
        if not file.exists():
            raise FileNotFoundError(f"File not found: {file}")

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self.converter.convert, file)
        markdown = result.document.export_to_markdown()

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
                "mime_type": "application/pdf",
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