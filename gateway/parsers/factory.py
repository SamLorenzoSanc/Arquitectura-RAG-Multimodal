from __future__ import annotations

from pathlib import Path

from .base import FileParser
from .docx_parser import DocxParser
from .image_parser import ImageParser
from .markdown_parser import MarkdownParser
from .pdf_parser import PdfParser
from .text_parser import TextParser


class FileParserFactory:

    @staticmethod
    def create(path: Path) -> FileParser:
        match path.suffix.lower():
            case ".pdf":
                return PdfParser()
            case ".docx":
                return DocxParser()
            case ".md":
                return MarkdownParser()
            case ".txt":
                return TextParser()
            case ".png" | ".jpg" | ".jpeg" | ".webp":
                return ImageParser()
            case _:
                raise ValueError(f"Unsupported file type: {path.suffix}")