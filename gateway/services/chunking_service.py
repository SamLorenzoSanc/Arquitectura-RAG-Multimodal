from __future__ import annotations

import json
import logging

from openai import OpenAI
from pydantic import BaseModel, Field
from tenacity import retry, wait_exponential
from schemas.chunk import Chunk, Chunks
from parsers.parsed_document import ParsedDocument

logger = logging.getLogger(__name__)

MODEL = "llama3"
AVERAGE_CHUNK_SIZE = 100

wait = wait_exponential(
    multiplier=1,
    min=5,
    max=120,
)

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)



class ChunkingService:

    def _make_prompt(
        self,
        document: ParsedDocument,
    ) -> str:

        how_many = (
            len(document.markdown) // AVERAGE_CHUNK_SIZE
        ) + 1

        return f"""
            Eres un sistema especializado en preparar documentos para un sistema RAG.
            
            Debes dividir el documento en fragmentos semánticos.
            
            El documento es:
            
            - nombre: {document.filename}
            - extensión: {document.extension}
            
            Genera aproximadamente {how_many} fragmentos.
            
            Reglas:
            
            - No omitas información.
            - Mantén un solapamiento aproximado del 20-25%.
            - Cada fragmento debe ser autocontenido.
            - Devuelve exclusivamente JSON.
            - Cada fragmento debe contener:
            
            headline
            summary
            original_text
            
            Documento:
            
            {document.markdown}
            """
            
    def _messages(
        self,
        document: ParsedDocument,
    ):

        return [
            {
                "role": "user",
                "content": self._make_prompt(document),
            }
        ]

    @retry(wait=wait)
    async def create_chunks(
        self,
        document: ParsedDocument,
    ) -> list[Chunk]:

        logger.info(
            "Creating semantic chunks for %s",
            document.filename,
        )

        response = client.beta.chat.completions.parse(

            model=MODEL,

            messages=self._messages(document),

            response_format=Chunks,
        )

        parsed = response.choices[0].message.parsed

        return parsed.chunks