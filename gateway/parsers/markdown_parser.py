from __future__ import annotations

import logging
from pathlib import Path

from .base import FileParser
from .parsed_document import ParsedDocument

logger = logging.getLogger(__name__)


class MarkdownParser(FileParser):

    async def parse(
        self,
        file: Path,
    ) -> ParsedDocument:

        markdown = file.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        return ParsedDocument(
            filename=file.name,
            extension=file.suffix.lower(),
            markdown=markdown.replace("\r\n", "\n").strip(),
            metadata={
                "source": str(file),
                "mime_type": "text/markdown",
            },
        )