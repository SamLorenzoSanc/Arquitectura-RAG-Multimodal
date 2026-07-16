from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass(slots=True)
class ParsedDocument:

    filename: str
    extension: str

    markdown: str

    title: str | None = None
    summary: str | None = None
    language: str | None = None

    page_count: int | None = None
    word_count: int | None = None
    character_count: int | None = None

    tags: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    extracted_at: datetime = field(default_factory=datetime.utcnow)