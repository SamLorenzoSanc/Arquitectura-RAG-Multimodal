from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from uuid import UUID

class Chunk(BaseModel):
    id: UUID
    document_id: UUID
    index: int

    headline: str
    summary: str
    original_text: str

    metadata: dict = {}

class Chunks(BaseModel):

    chunks: list[Chunk]