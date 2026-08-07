from __future__ import annotations

import base64
import hashlib
import logging
import mimetypes
from datetime import datetime, timezone
from pathlib import Path

from openai import AsyncOpenAI

from .base import FileParser, ParsingContext
from .parsed_document import ParsedDocument

logger = logging.getLogger(__name__)


class ImageParser(FileParser):

    SUPPORTED_FORMATS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
    }

    def __init__(
        self,
        model: str = "llama3.2-vision",
        base_url: str = "http://localhost:11434/v1",
    ) -> None:

        self.model = model

        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key="ollama",
        )

    def _get_mime_type(
        self,
        file: Path,
    ) -> str:
        """
        Obtiene el MIME real del fichero.
        """

        mime_type, _ = mimetypes.guess_type(file.name)

        if mime_type is None:
            raise ValueError(f"Unsupported image format: {file.suffix}")

        if not mime_type.startswith("image/"):
            raise ValueError(f"File is not an image: {mime_type}")

        return mime_type

    def _validate_format(
        self,
        file: Path,
    ) -> None:
        """
        Valida extensiones soportadas.
        """

        extension = file.suffix.lower()

        if extension not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported image format: {extension}")

    async def parse(
        self,
        file: Path,
        context: ParsingContext,
    ) -> ParsedDocument:

        if not file.exists():
            raise FileNotFoundError(f"File not found: {file}")

        if not file.is_file():
            raise ValueError(f"{file} is not a valid file")

        self._validate_format(file)

        logger.info(
            "Parsing image %s",
            file,
        )

        markdown = await self._convert(file)

        checksum = hashlib.sha256(file.read_bytes()).hexdigest()

        return ParsedDocument(
            filename=file.name,
            extension=file.suffix.lower(),
            title=file.stem,
            markdown=markdown.strip(),
            language=context.language or "es",
            word_count=len(markdown.split()),
            character_count=len(markdown),
            metadata={
                "source": str(file),
                "mime_type": self._get_mime_type(file),
                "parser": "vision-llm",
                "model": self.model,
                "size": file.stat().st_size,
                "checksum": checksum,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "tenant_id": str(context.tenant_id),
                "organization_id": (
                    str(context.organization_id) if context.organization_id else None
                ),
                "department_id": (
                    str(context.department_id) if context.department_id else None
                ),
                "member_id": (str(context.member_id) if context.member_id else None),
                "uploaded_by": (
                    str(context.uploaded_by) if context.uploaded_by else None
                ),
                "tags": context.tags,
            },
        )

    async def _convert(
        self,
        file: Path,
    ) -> str:

        image_bytes = file.read_bytes()

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        mime_type = self._get_mime_type(file)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un parser documental.\n"
                        "Tu objetivo es convertir cualquier imagen "
                        "en Markdown estructurado.\n\n"
                        "Reglas:\n"
                        "- Extrae TODO el texto visible.\n"
                        "- Mantén la jerarquía de títulos.\n"
                        "- Convierte listas correctamente.\n"
                        "- Convierte tablas a Markdown cuando sea posible.\n"
                        "- Describe diagramas y gráficos.\n"
                        "- Describe imágenes relevantes.\n"
                        "- No inventes información.\n"
                        "- Si hay texto ilegible, indícalo.\n"
                        "- Devuelve únicamente Markdown."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": ("Convierte esta imagen a Markdown."),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": (f"data:{mime_type};base64," f"{image_b64}")
                            },
                        },
                    ],
                },
            ],
        )

        return response.choices[0].message.content or ""
