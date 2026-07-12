from __future__ import annotations

import logging
from pathlib import Path

from .base import FileParser

logger = logging.getLogger(__name__)


class MarkdownParser(FileParser):
    """
    Parser para documentos Markdown.

    No realiza ninguna conversión, simplemente carga el contenido
    del fichero para que el resto del pipeline (chunking, embeddings,
    knowledge graph...) trabaje sobre él.
    """

    async def parse(self, file: Path) -> str:

        if not file.exists():
            raise FileNotFoundError(file)

        if not file.is_file():
            raise ValueError(f"{file} is not a valid file")

        logger.info("Parsing Markdown %s", file)

        markdown = file.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        # Normalizar saltos de línea
        markdown = markdown.replace("\r\n", "\n")

        return markdown.strip()