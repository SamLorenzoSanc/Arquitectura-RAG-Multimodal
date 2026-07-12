from pathlib import Path

from .pdf_parser import PdfParser
from .docx_parser import DocxParser
from .markdown_parser import MarkdownParser
from .text_parser import TextParser

class FileParserFactory:

    @staticmethod
    def create(path: Path):

        ext = path.suffix.lower()

        match ext:
            case ".pdf":
                return PdfParser()
            case ".docx":
                return DocxParser()
            case ".md":
                return MarkdownParser()
            case ".txt":
                return TextParser()
            case _:
                raise ValueError(
                    f"Unsupported file type {ext}"
                )