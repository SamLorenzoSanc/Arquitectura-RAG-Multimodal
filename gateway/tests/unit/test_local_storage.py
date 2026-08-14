"""Tests del storage local de documentos."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from storage.local import LocalFileStorage

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_local_storage_save_load_delete(tmp_path: Path):
    storage = LocalFileStorage(root=tmp_path)
    upload = AsyncMock()
    upload.filename = "manual.pdf"
    upload.read = AsyncMock(return_value=b"%PDF-demo")

    saved = await storage.save(upload, "tenant-1", "kb-1")
    path = Path(saved)
    assert path.exists()
    assert path.read_bytes() == b"%PDF-demo"

    by_bytes = await storage.save_bytes(b"bytes-ok", "nota.txt", "tenant-1", "kb-1")
    assert Path(by_bytes).read_bytes() == b"bytes-ok"

    loaded = await storage.load(saved)
    assert loaded == path

    await storage.delete(saved)
    assert not path.exists()


@pytest.mark.asyncio
async def test_local_storage_load_missing(tmp_path: Path):
    storage = LocalFileStorage(root=tmp_path)
    with pytest.raises(FileNotFoundError):
        await storage.load(str(tmp_path / "missing.pdf"))
