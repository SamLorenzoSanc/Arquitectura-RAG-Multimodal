from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from services.embedding_reindex import (
    EMBEDDING_CATALOG,
    chunk_text,
    ensure_document_chunks,
    extract_index_text,
    pad_vector,
    record_reindex_on_job,
    split_into_chunks,
)

pytestmark = pytest.mark.unit


def test_pad_vector_keeps_cosine_compatible_zeros():
    padded = pad_vector([1.0, 0.0, 0.0], dim=6)
    assert padded == [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    assert pad_vector([1, 2, 3, 4], dim=3) == [1, 2, 3]


def test_chunk_text_joins_parts():
    assert "título" in chunk_text("título", None, "cuerpo")
    assert chunk_text("", "", "") == ""


def test_embedding_catalog_has_qwen_and_baseline():
    ids = {item["id"] for item in EMBEDDING_CATALOG}
    assert "qwen3-embedding:latest" in ids
    assert "nomic-embed-text" in ids


def test_split_into_chunks_respects_size():
    body = ("palabra " * 400).strip()
    parts = split_into_chunks(body, size=80, overlap=10)
    assert len(parts) > 1
    assert all(len(part) <= 80 for part in parts)
    assert split_into_chunks("") == []
    assert split_into_chunks("corto") == ["corto"]


def test_extract_index_text_plain():
    assert "hola" in extract_index_text("nota.txt", b"hola mundo", "text/plain")


def test_extract_index_text_pptx_slides():
    from io import BytesIO
    from zipfile import ZipFile

    slide = (
        b'<?xml version="1.0"?><p:sld xmlns:a="http://a" xmlns:p="http://p">'
        b"<a:t>Riego por goteo</a:t></p:sld>"
    )
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", slide)
    text = extract_index_text("charla.pptx", buffer.getvalue(), "application/pptx")
    assert "Riego por goteo" in text


@pytest.mark.asyncio
async def test_ensure_document_chunks_skips_when_present():
    db = AsyncMock()
    count = MagicMock()
    count.scalar.return_value = 3
    db.execute = AsyncMock(return_value=count)
    created = await ensure_document_chunks(db, str(uuid4()))
    assert created == 3
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_document_chunks_creates_from_txt(tmp_path: Path):
    path = tmp_path / "nota.txt"
    path.write_text("Párrafo uno.\n\n" + ("texto " * 400), encoding="utf-8")
    db = AsyncMock()
    count = MagicMock()
    count.scalar.return_value = 0
    mappings = MagicMock()
    mappings.first.return_value = {
        "id": str(uuid4()),
        "filename": "nota.txt",
        "mime_type": "text/plain",
        "storage_path": str(path),
    }
    doc_result = MagicMock()
    doc_result.mappings.return_value = mappings
    db.execute = AsyncMock(side_effect=[count, doc_result])
    db.add = MagicMock()
    created = await ensure_document_chunks(db, str(uuid4()))
    assert created >= 1
    assert db.add.call_count == created
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_record_reindex_on_job_updates_existing():
    db = AsyncMock()
    updated = MagicMock()
    updated.rowcount = 1
    db.execute = AsyncMock(return_value=updated)
    await record_reindex_on_job(
        db,
        document_id=str(uuid4()),
        tenant_id=str(uuid4()),
        models=["qwen3-embedding:latest"],
        result={
            "chunks": 4,
            "models": {
                "qwen3-embedding:latest": {
                    "indexed": 4,
                    "skipped": 0,
                    "failed": 0,
                }
            },
        },
    )
    db.commit.assert_awaited()
    sql = str(db.execute.await_args_list[0].args[0])
    assert "UPDATE processing_jobs" in sql
