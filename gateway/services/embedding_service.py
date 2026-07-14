from __future__ import annotations

import logging

from openai import OpenAI

from schemas.embedded_chunk import EmbeddedChunk
from services.chunking_service import Chunk

logger = logging.getLogger(__name__)


EMBEDDING_MODEL = "qwen3-embedding:latest"


client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)


class EmbeddingService:

    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
    ):

        self.model = model

    async def create_embeddings(
        self,
        chunks: list[Chunk],
    ) -> list[EmbeddedChunk]:

        logger.info(
            "Creating embeddings (%s chunks)",
            len(chunks),
        )

        texts = [

            f"{chunk.headline}\n\n"
            f"{chunk.summary}\n\n"
            f"{chunk.original_text}"

            for chunk in chunks
        ]

        response = client.embeddings.create(

            model=self.model,

            input=texts,
        )

        embeddings = []

        for chunk, emb in zip(chunks, response.data):

            embeddings.append(

                EmbeddedChunk(

                    chunk=chunk,

                    embedding=emb.embedding,
                )
            )

        logger.info(
            "Created %s embeddings",
            len(embeddings),
        )

        return embeddings