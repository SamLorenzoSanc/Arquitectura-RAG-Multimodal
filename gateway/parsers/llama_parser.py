from __future__ import annotations

import hashlib
import logging
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path

from llama_parse import LlamaParse

from .base import FileParser, ParsingContext
from .parsed_document import ParsedDocument

logger = logging.getLogger(__name__)


class LlamaParseParser(FileParser):
    """
    Parser basado en LlamaParse para documentos complejos
    (PDF, DOCX, PPTX, XLSX, HTML, etc.).
    """

    def __init__(
        self,
        api_key: str | None = None,
        result_type: str = "markdown",
        verbose: bool = False,
    ) -> None:
        """
        Inicializa el cliente de LlamaParse.

        Si no se provee `api_key`, la librería buscará la variable
        de entorno `LLAMA_CLOUD_API_KEY`.
        """
        self.api_key = api_key or os.getenv("LLAMA_CLOUD_API_KEY")
        if not self.api_key:
            logger.warning(
                "LLAMA_CLOUD_API_KEY no encontrada. Asegúrate de configurarla en tu entorno."
            )

        self.parser = LlamaParse(
            api_key=self.api_key,
            result_type=result_type,
            num_workers=4,
            verbose=verbose,
        )

    def _get_mime_type(self, file: Path) -> str:
        """Obtiene el tipo MIME del archivo o devuelve octet-stream por defecto."""
        mime_type, _ = mimetypes.guess_type(file.name)
        return mime_type or "application/octet-stream"

    async def parse(
        self,
        file: Path,
        context: ParsingContext,
    ) -> ParsedDocument:
        if not file.exists():
            raise FileNotFoundError(f"File not found: {file}")

        if not file.is_file():
            raise ValueError(f"{file} is not a valid file")

        logger.info("Parsing document %s with LlamaParse", file)

        # Ingesta asíncrona del documento
        documents = await self.parser.aload_data(str(file))

        # Unimos el texto Markdown devuelto en todas las páginas/nodos
        markdown = "\n\n".join([doc.text for doc in documents if doc.text]).strip()

        checksum = hashlib.sha256(file.read_bytes()).hexdigest()
        mime_type = self._get_mime_type(file)

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
                "mime_type": mime_type,
                "parser": "llama-parse",
                "size": file.stat().st_size,
                "checksum": checksum,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "tenant_id": str(context.tenant_id),
                "organization_id": (
                    str(context.organization_id) if context.organization_id else None
                ),
                "department_id": (
                    str(context.department_id) if context.department_id else None
                ),
                "member_id": (str(context.member_id) if context.member_id else None),
                "uploaded_by": (
                    str(context.uploaded_by) if context.uploaded_by else None
                ),
                "tags": context.tags,
            },
        )
