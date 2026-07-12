from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from uuid import UUID

class Chunk(BaseModel):
    headline: str
    summary: str
    original_text: str

class ChunkCollection(BaseModel):
    chunks: list[Chunk]