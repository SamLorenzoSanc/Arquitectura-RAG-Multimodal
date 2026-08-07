from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from pathlib import Path

from .base import FileParser
from .parsed_document import ParsedDocument

logger = logging.getLogger(__name__)


class TextParser(FileParser):
    """
    Parser para archivos de texto plano (.txt).
    """

    async def parse(
        self,
        file: Path,
    ) -> ParsedDocument:

        if not file.exists():
            raise FileNotFoundError(file)

        if not file.is_file():
            raise ValueError(f"{file} is not a valid file")

        logger.info("Parsing text file %s", file)

        markdown = (
            file.read_text(
                encoding="utf-8",
                errors="ignore",
            )
            .replace("\r\n", "\n")
            .strip()
        )

        checksum = hashlib.sha256(file.read_bytes()).hexdigest()

        return ParsedDocument(
            filename=file.name,
            extension=file.suffix.lower(),
            title=file.stem,
            markdown=markdown,
            language="es",
            word_count=len(markdown.split()),
            character_count=len(markdown),
            metadata={
                "source": str(file),
                "mime_type": "text/plain",
                "parser": "native",
                "size": file.stat().st_size,
                "checksum": checksum,
                "created_at": datetime.utcnow().isoformat(),
            },
        )
