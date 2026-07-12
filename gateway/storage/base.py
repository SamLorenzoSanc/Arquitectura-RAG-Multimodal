from abc import ABC, abstractmethod
from pathlib import Path


class FileStorage(ABC):

    @abstractmethod
    async def save(
        self,
        file,
        tenant_id,
        knowledge_base_id,
    ) -> str:
        ...

    @abstractmethod
    async def delete(
        self,
        path: str,
    ):
        ...

    @abstractmethod
    async def load(
        self,
        path: str,
    ) -> Path:
        ...