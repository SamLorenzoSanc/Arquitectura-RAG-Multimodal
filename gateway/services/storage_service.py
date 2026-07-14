

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile


class StorageService:

    STORAGE_ROOT = Path("../storage")

    def __init__(self):

        self.STORAGE_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

    async def save(
        self,
        file: UploadFile,
        tenant_id: UUID,
        knowledge_base_id: UUID,
    ) -> Path:

        extension = Path(file.filename).suffix

        filename = f"{uuid4()}{extension}"

        folder = (
            self.STORAGE_ROOT
            / str(tenant_id)
            / str(knowledge_base_id)
        )

        folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = folder / filename

        file.file.seek(0)

        with destination.open("wb") as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

        return destination

    async def delete(
        self,
        file: Path,
    ):

        if file.exists():

            file.unlink()

    async def exists(
        self,
        file: Path,
    ) -> bool:

        return file.exists()