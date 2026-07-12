from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class ParsedDocument(BaseModel):
    filename: str
    extension: str
    markdown: str

    metadata: dict = Field(default_factory=dict)

    images: list[str] = Field(default_factory=list)

    tables: list[str] = Field(default_factory=list)