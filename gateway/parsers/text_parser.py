from __future__ import annotations

import logging
from pathlib import Path

from .base import FileParser
from .parsed_document import ParsedDocument

logger = logging.getLogger(__name__)


class TextParser(FileParser):
    """
    Parser para archivos de texto plano (.txt).
    """

    async def parse(self, file: Path) -> ParsedDocument:

        if not file.exists():
            raise FileNotFoundError(file)

        if not file.is_file():
            raise ValueError(f"{file} is not a valid file")

        logger.info("Parsing text file %s", file)

        text = file.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        return ParsedDocument(
            filename=file.name,
            extension=file.suffix.lower(),
            markdown=text.replace("\r\n", "\n").strip(),
            metadata={
                "source": str(file),
                "mime_type": "text/plain",
            },
        )