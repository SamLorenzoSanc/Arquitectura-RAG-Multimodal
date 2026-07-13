from __future__ import annotations

import asyncio
from pathlib import Path

# Importaciones necesarias para configurar el backend y el pipeline
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, OcrMacOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend  # El backend recomendado

from .base import FileParser
from .parsed_document import ParsedDocument


class PdfParser(FileParser):

    def __init__(self):
        # 1. Configurar las opciones del pipeline de PDF
        pipeline_options = PdfPipelineOptions()
        
        # Estrategia inteligente: "auto" intenta extraer texto nativo primero y 
        # solo hace OCR en imágenes/escaneos dentro del PDF si es necesario.
        # Si aun así falla, puedes cambiarlo directamente a False.
        pipeline_options.do_ocr = True 
        
        # 2. Configurar las opciones específicas de formato para PDF
        pdf_options = PdfFormatOption(
            pipeline_options=pipeline_options,
            backend=PyPdfiumDocumentBackend  # Cambiamos al backend de pypdfium2 para evitar bloqueos
        )

        # 3. Inicializar el convertidor con la configuración optimizada
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: pdf_options
            }
        )

    async def parse(self, file: Path) -> ParsedDocument:
        # Ejecutar en ejecutor para evitar colgar el loop de asyncio con PDFs pesados
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self.converter.convert, file)

        return ParsedDocument(
            filename=file.name,
            extension=file.suffix.lower(),
            markdown=result.document.export_to_markdown(),
            metadata={
                "source": str(file),
                "mime_type": "application/pdf",
                "parser": "docling",
            },
        )

    def _convert(self, file: Path) -> str:
        rendered = self.converter.convert(file)
        return rendered.document.export_to_markdown()