from __future__ import annotations

from pydantic import BaseModel

from .chunk import Chunk


class EmbeddedChunk(BaseModel):

    chunk: Chunk

    embedding: list[float]