from __future__ import annotations

import json
import logging

from openai import OpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


OLLAMA_BASE_URL = "http://localhost:11434/v1"
LLM_MODEL = "qwen3:latest"
AVERAGE_CHUNK_SIZE = 100


class Chunk(BaseModel):
    """
    Representa un fragmento semántico del documento.
    """

    headline: str = Field(
        description="Título breve del fragmento."
    )

    summary: str = Field(
        description="Resumen del fragmento."
    )

    original_text: str = Field(
        description="Texto original del documento."
    )

    metadata: dict = Field(
        default_factory=dict
    )

    entities: list[str] = Field(
        default_factory=list
    )

    relations: list[dict] = Field(
        default_factory=list
    )


class ChunkCollection(BaseModel):

    chunks: list[Chunk]


class ChunkingService:

    def __init__(
        self,
        model: str = LLM_MODEL,
        base_url: str = OLLAMA_BASE_URL,
    ):

        self.model = model

        self.client = OpenAI(
            base_url=base_url,
            api_key="ollama",
        )

    async def chunk(
        self,
        markdown: str,
        metadata: dict | None = None,
    ) -> list[Chunk]:

        if metadata is None:
            metadata = {}

        logger.info(
            "Generating semantic chunks using %s",
            self.model,
        )

        prompt = self._build_prompt(
            markdown,
            metadata,
        )

        response = self.client.chat.completions.create(

            model=self.model,

            temperature=0,

            response_format={
                "type": "json_object"
            },

            messages=[
                {
                    "role": "system",
                    "content": """
                        Eres un experto en sistemas RAG.

                        Tu trabajo consiste únicamente en dividir documentos
                        en fragmentos semánticos.

                        Siempre respondes únicamente JSON válido.

                        Nunca añadas texto fuera del JSON.
                        """,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        try:

            data = json.loads(
                response.choices[0].message.content
            )

            collection = ChunkCollection.model_validate(
                data
            )

        except Exception:

            logger.exception(
                "Invalid JSON returned by LLM"
            )

            raise

        for chunk in collection.chunks:

            chunk.metadata = metadata

        logger.info(
            "Generated %d chunks",
            len(collection.chunks),
        )

        return collection.chunks

    def _build_prompt(
        self,
        markdown: str,
        metadata: dict,
    ) -> str:

        source = metadata.get(
            "source",
            "unknown",
        )

        document_type = metadata.get(
            "type",
            "document",
        )

        estimated_chunks = (
            len(markdown) // AVERAGE_CHUNK_SIZE
        ) + 1

        return f"""
            Debes convertir el siguiente documento Markdown en una colección de
            fragmentos semánticos para un sistema RAG.

            Información del documento

            Tipo:
            {document_type}

            Origen:
            {source}

            Número aproximado de fragmentos:
            {estimated_chunks}

            Cada fragmento debe contener:

            - headline
            - summary
            - original_text

            Normas:

            - No inventes contenido.
            - Conserva exactamente el texto original.
            - Todo el documento debe quedar cubierto.
            - Puede existir solapamiento entre fragmentos.
            - El headline debe ser corto.
            - El summary debe tener entre una y tres frases.
            Responde únicamente con este JSON:

            {{
                "chunks": [
                    {{
                        "headline": "",
                        "summary": "",
                        "original_text": ""
                    }}
                ]
            }}

            Documento:

            -----------------------------------------

            {markdown}

            -----------------------------------------
            """