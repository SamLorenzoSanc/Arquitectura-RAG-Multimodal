from __future__ import annotations

import base64
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from openai import AsyncOpenAI

from .base import FileParser, ParsingContext
from .parsed_document import ParsedDocument

logger = logging.getLogger(__name__)


class ImageParser(FileParser):

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

    async def parse(
        self,
        file: Path,
        context: ParsingContext,
    ) -> ParsedDocument:
        if not file.exists():
            raise FileNotFoundError(f"File not found: {file}")

        if not file.is_file():
            raise ValueError(f"{file} is not a valid file")

        logger.info("Parsing image %s", file)

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
                "mime_type": f"image/{file.suffix.lower().lstrip('.')}",
                "parser": "vision-llm",
                "model": self.model,
                "size": file.stat().st_size,
                "checksum": checksum,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "tenant_id": str(context.tenant_id),
                "organization_id": str(context.organization_id) if context.organization_id else None,
                "department_id": str(context.department_id) if context.department_id else None,
                "member_id": str(context.member_id) if context.member_id else None,
                "uploaded_by": str(context.uploaded_by) if context.uploaded_by else None,
                "tags": context.tags,
            },
        )

    async def _convert(self, file: Path) -> str:
        image_bytes = file.read_bytes()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un parser documental.\n"
                        "Tu objetivo es convertir cualquier imagen en Markdown estructurado.\n\n"
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
                        {"type": "text", "text": "Convierte esta imagen a Markdown."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        },
                    ],
                },
            ],
        )
        return response.choices[0].message.content or ""