from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from uuid import UUID

from .parsed_document import ParsedDocument


@dataclass(slots=True)
class ParsingContext:
    tenant_id: UUID
    organization_id: UUID | None = None
    department_id: UUID | None = None
    member_id: UUID | None = None
    uploaded_by: UUID | None = None
    language: str | None = None
    tags: list[str] | None = None

class FileParser(ABC):

    @abstractmethod
    async def parse(
        self,
        file: Path,
        context: ParsingContext,
    ) -> ParsedDocument:
        """
        Convierte cualquier documento a un ParsedDocument.
        """
        pass
    