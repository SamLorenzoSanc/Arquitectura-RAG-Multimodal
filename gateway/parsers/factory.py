from pathlib import Path

from .pdf_parser import PdfParser
from .docx_parser import DocxParser
from .markdown_parser import MarkdownParser
from .text_parser import TextParser
from .image_parser import ImageParser


class FileParserFactory:

    @staticmethod
    def create(path: Path):

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
                raise ValueError(
                    f"Unsupported file type: {path.suffix}"
                )