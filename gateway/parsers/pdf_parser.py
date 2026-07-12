from __future__ import annotations

import asyncio
from pathlib import Path

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

from .base import FileParser


class PdfParser(FileParser):

    def __init__(self):

        self.converter = PdfConverter(
            artifact_dict=create_model_dict()
        )

    async def parse(
        self,
        file: Path,
    ) -> str:

        loop = asyncio.get_running_loop()

        markdown = await loop.run_in_executor(
            None,
            self._convert,
            file,
        )

        return markdown

    def _convert(
        self,
        file: Path,
    ) -> str:

        rendered = self.converter(file)

        return rendered.markdown