from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from services.embedding_reindex import (
    EMBEDDING_CATALOG,
    _ensure_model_available,
    chunk_text,
    embedding_payload,
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


def test_embedding_payload_skips_duplicate_headline():
    body = "El riego por goteo reduce pérdidas de agua."
    assert embedding_payload("El riego por goteo", body[:20], body) == body
    assert embedding_payload("titular", "resumen", "") == "titular\n\nresumen"


def test_embed_batch_uses_native_ollama_api():
    from services.embedding_reindex import _embed_batch

    client = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"embeddings": [[1.0, 0.0], [0.0, 1.0]]}
    client.post.return_value = response
    client.is_closed = False

    import services.embedding_reindex as mod

    previous = mod._HTTP
    mod._HTTP = client
    try:
        vectors = _embed_batch("qwen3-embedding:latest", ["a", "b"])
    finally:
        mod._HTTP = previous

    assert client.post.call_args.args[0].endswith("/api/embed")
    assert client.post.call_args.kwargs["json"]["input"] == ["a", "b"]
    assert len(vectors) == 2
    assert vectors[0][0] == 1.0


def test_embedding_catalog_has_qwen_and_baseline():
    ids = {item["id"] for item in EMBEDDING_CATALOG}
    assert "qwen3-embedding:latest" in ids
    assert "nomic-embed-text" in ids


def test_ensure_model_available_pulls_only_missing_model():
    client = MagicMock()
    tags = MagicMock()
    tags.json.return_value = {
        "models": [{"name": "qwen3-embedding:latest"}]
    }
    client.get.return_value = tags
    client.post.return_value = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = client
    context.__exit__.return_value = False

    with patch("services.embedding_reindex.httpx.Client", return_value=context):
        _ensure_model_available("qwen3-embedding:latest")
        client.post.assert_not_called()
        _ensure_model_available("nomic-embed-text")

    pull_call = client.post.call_args
    assert pull_call.args[0].endswith("/api/pull")
    assert pull_call.kwargs["json"] == {
        "name": "nomic-embed-text",
        "stream": False,
    }


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


def test_extract_index_text_transcribes_video(monkeypatch):
    monkeypatch.setattr(
        "services.embedding_reindex.transcribe_video_text",
        lambda *_args, **_kwargs: "[0.0s–2.1s] Revisa el filtro de malla.",
    )
    text = extract_index_text("riego.mp4", b"\x00\x01\x02not-utf8", "video/mp4")
    assert "filtro de malla" in text


def test_extract_index_text_does_not_decode_video_bytes():
    from services.video_extract import is_video_file

    assert is_video_file("charla.webm", "video/webm")
    assert is_video_file("nota.mp3", "audio/mpeg")
    assert not is_video_file("posei.pdf", "application/pdf")


@pytest.mark.asyncio
async def test_ensure_document_chunks_skips_when_present():
    db = AsyncMock()
    count = MagicMock()
    count.scalar.return_value = 3
    sample = MagicMock()
    sample.all.return_value = [
        (
            "El riego por goteo reduce pérdidas de agua en la platanera canaria durante el verano.",
        )
    ]
    db.execute = AsyncMock(side_effect=[count, sample])
    created = await ensure_document_chunks(db, str(uuid4()))
    assert created == 3
    db.add.assert_not_called()
    db.add_all.assert_not_called()


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
    db.add_all.assert_called_once()
    stored = db.add_all.call_args.args[0]
    assert len(stored) == created
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_ensure_document_chunks_rebuilds_garbled(tmp_path: Path):
    path = tmp_path / "posei.txt"
    path.write_text(
        "Resolución del segundo pago de la subvención POSEI 2025 en Canarias.\n\n"
        + ("texto " * 400),
        encoding="utf-8",
    )
    db = AsyncMock()
    count = MagicMock()
    count.scalar.return_value = 3
    sample = MagicMock()
    sample.all.return_value = [("\ufffd" * 120,)]
    delete_emb = MagicMock()
    delete_chunks = MagicMock()
    mappings = MagicMock()
    mappings.first.return_value = {
        "id": str(uuid4()),
        "filename": "posei.txt",
        "mime_type": "text/plain",
        "storage_path": str(path),
    }
    doc_result = MagicMock()
    doc_result.mappings.return_value = mappings
    db.execute = AsyncMock(
        side_effect=[count, sample, delete_emb, delete_chunks, doc_result]
    )
    db.add = MagicMock()
    created = await ensure_document_chunks(db, str(uuid4()))
    assert created >= 1
    db.add_all.assert_called_once()
    sqls = [str(call.args[0]) for call in db.execute.await_args_list]
    assert any("DELETE FROM embeddings" in sql for sql in sqls)
    assert any("DELETE FROM chunks" in sql for sql in sqls)


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
