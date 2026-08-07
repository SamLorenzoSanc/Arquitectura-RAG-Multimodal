from __future__ import annotations

from pathlib import Path

from .base import FileParser
from .image_parser import ImageParser
from .llama_parser import LlamaParseParser
from .markdown_parser import MarkdownParser
from .text_parser import TextParser


class FileParserFactory:

    @staticmethod
    def create(path: Path) -> FileParser:
        match path.suffix.lower():
            case (
                ".pdf"
                | ".docx"
                | ".doc"
                | ".pptx"
                | ".ppt"
                | ".xlsx"
                | ".epub"
                | ".html"
            ):
                return LlamaParseParser()

            case ".md":
                return MarkdownParser()
            case ".txt":
                return TextParser()

            case ".png" | ".jpg" | ".jpeg" | ".webp":
                return ImageParser()

            case _:
                raise ValueError(f"Unsupported file type: {path.suffix}")
