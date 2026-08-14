"""Almacenamiento local de documentos para la ingesta del monolito."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from storage.base import FileStorage

# Fuera del paquete Python para no mezclar código y binarios de upload.
DEFAULT_ROOT = Path(
    os.getenv(
        "DOCUMENT_STORAGE_ROOT", Path(__file__).resolve().parent.parent / "uploads"
    )
)


class LocalFileStorage(FileStorage):
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root else DEFAULT_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def _target_dir(self, tenant_id, knowledge_base_id) -> Path:
        path = self.root / str(tenant_id) / str(knowledge_base_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def save_bytes(
        self, content: bytes, filename: str | None, tenant_id, knowledge_base_id
    ) -> str:
        safe_name = Path(filename or f"{uuid.uuid4()}.bin").name
        target = (
            self._target_dir(tenant_id, knowledge_base_id)
            / f"{uuid.uuid4()}_{safe_name}"
        )
        target.write_bytes(content)
        return str(target)

    async def save(self, file, tenant_id, knowledge_base_id) -> str:
        filename = getattr(file, "filename", None) or f"{uuid.uuid4()}.bin"
        content = await file.read()
        return await self.save_bytes(content, filename, tenant_id, knowledge_base_id)

    async def delete(self, path: str):
        file_path = Path(path)
        if file_path.exists():
            file_path.unlink()

    async def load(self, path: str) -> Path:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(path)
        return file_path
