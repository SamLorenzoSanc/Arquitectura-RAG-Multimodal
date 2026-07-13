from abc import ABC, abstractmethod
from pathlib import Path

from .parsed_document import ParsedDocument


class FileParser(ABC):

    @abstractmethod
    async def parse(
        self,
        file: Path,
    ) -> ParsedDocument:
        """
        Convierte cualquier documento a un ParsedDocument.
        """
        pass