from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from marker.converters.document import DocumentConverter
from marker.models import create_model_dict

from .base import FileParser
from .parsed_document import ParsedDocument

logger = logging.getLogger(__name__)


class DocxParser(FileParser):
    """
    Parser de documentos DOCX utilizando Marker.

    Convierte el documento a Markdown preservando:

    - Encabezados
    - Tablas
    - Listas
    - Imágenes
    - Hipervínculos
    """

    def __init__(self):

        self.converter = DocumentConverter(
            artifact_dict=create_model_dict()
        )

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
                "parser": "marker",
            },
        )

    def _convert(
        self,
        file: Path,
    ) -> str:

        rendered = self.converter(file)

        return rendered.markdown