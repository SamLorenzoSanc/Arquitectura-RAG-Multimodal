"""Reindexado de chunks con varios modelos de embedding (un vector por par chunk×modelo)."""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
from openai import OpenAI
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.chunk import Chunk
from models.embedding import Embedding
from services.pdf_extract import corpus_looks_corrupted, extract_pdf_text, is_readable_text
from services.rag_service import DEFAULT_EMBEDDING_MODEL
from services.video_extract import is_video_file, transcribe_video_text

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_URL = os.getenv(
    "OLLAMA_URL", OLLAMA_BASE_URL.removesuffix("/v1")
).rstrip("/")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")
VECTOR_DIM = 4096
BATCH_SIZE = max(8, int(os.getenv("RAG_EMBED_BATCH_SIZE", "64")))
CHUNK_SIZE = max(400, int(os.getenv("RAG_CHUNK_SIZE", "1400")))
CHUNK_OVERLAP = max(0, int(os.getenv("RAG_CHUNK_OVERLAP", "120")))
MAX_INDEX_CHARS = 400_000
MAX_PDF_PAGES = max(1, int(os.getenv("RAG_PDF_MAX_PAGES", "120")))
_SCHEMA_READY = False
_HTTP: httpx.Client | None = None

EMBEDDING_CATALOG = [
    {
        "id": "nomic-embed-text",
        "label": "Nomic Embed Text",
        "why": "Por defecto: ligero (~274 MB), deja VRAM al chatbot Llama 3.2.",
    },
    {
        "id": "qwen3-embedding:latest",
        "label": "Qwen3 Embedding",
        "why": "Más capaz en español técnico; ocupa ~6 GB de VRAM.",
    },
    {
        "id": "mxbai-embed-large",
        "label": "mixedbread large",
        "why": "Embedding denso de mayor capacidad semántica.",
    },
    {
        "id": "bge-m3",
        "label": "BGE-M3",
        "why": "Multilingüe; contraste frente a Nomic en normativa.",
    },
]

ENSURE_MULTI_EMBEDDING_SQL = (
    "ALTER TABLE public.embeddings DROP CONSTRAINT IF EXISTS embeddings_chunk_id_key",
    "DROP INDEX IF EXISTS embeddings_chunk_id_key",
    "DROP INDEX IF EXISTS ix_embeddings_chunk_id",
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ux_embeddings_chunk_model
    ON public.embeddings (chunk_id, model)
    """,
)


def pad_vector(values: list[float], dim: int = VECTOR_DIM) -> list[float]:
    if len(values) >= dim:
        return list(values[:dim])
    return list(values) + [0.0] * (dim - len(values))


def chunk_text(headline: str | None, summary: str | None, content: str | None) -> str:
    return "\n\n".join(
        part for part in [headline, summary, content] if part and str(part).strip()
    ).strip()


def embedding_payload(
    headline: str | None, summary: str | None, content: str | None
) -> str:
    """El vector sale del cuerpo del fragmento; no reenvía titular y resumen."""
    body = (content or "").strip()
    if body:
        return body
    return chunk_text(headline, summary, content) or " "


def split_into_chunks(
    text: str,
    size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    cleaned = re.sub(r"\r\n", "\n", text or "").strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    if not cleaned:
        return []
    if len(cleaned) <= size:
        return [cleaned]
    parts: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + size)
        if end < len(cleaned):
            window = cleaned[start:end]
            cut = window.rfind("\n\n")
            if cut < size * 0.4:
                cut = window.rfind("\n")
            if cut < size * 0.4:
                cut = window.rfind(" ")
            if cut >= size * 0.4:
                end = start + cut
        piece = cleaned[start:end].strip()
        if piece:
            parts.append(piece)
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return parts


def extract_index_text(
    filename: str, content: bytes, mime_type: str | None = None
) -> str:
    name = (filename or "").lower()
    mime = (mime_type or "").lower()
    if name.endswith((".txt", ".md", ".csv", ".json", ".html", ".xml")) or mime.startswith(
        "text/"
    ):
        return content.decode("utf-8", errors="ignore")[:MAX_INDEX_CHARS]

    if name.endswith(".docx") or "wordprocessingml" in mime:
        extracted = _extract_office_xml_text(
            content, member="word/document.xml", prefix=None
        )
        if extracted:
            return extracted[:MAX_INDEX_CHARS]

    if name.endswith((".pptx", ".ppt")) or "presentationml" in mime:
        extracted = _extract_office_xml_text(
            content, member=None, prefix="ppt/slides/slide"
        )
        if extracted:
            return extracted[:MAX_INDEX_CHARS]

    if name.endswith(".pdf") or "pdf" in mime:
        return extract_pdf_text(
            content, max_pages=MAX_PDF_PAGES, max_chars=MAX_INDEX_CHARS
        )

    if is_video_file(filename, mime_type):
        return transcribe_video_text(content, filename, max_chars=MAX_INDEX_CHARS)

    return content.decode("utf-8", errors="ignore")[:MAX_INDEX_CHARS]


def _extract_office_xml_text(
    content: bytes,
    *,
    member: str | None,
    prefix: str | None,
) -> str:
    """Lee nodos de texto de DOCX/PPTX sin pasar por LlamaParse."""
    try:
        from io import BytesIO
        from zipfile import ZipFile
        import xml.etree.ElementTree as ET

        with ZipFile(BytesIO(content)) as archive:
            names: list[str]
            if member:
                names = [member]
            else:
                names = sorted(
                    name
                    for name in archive.namelist()
                    if prefix and name.startswith(prefix) and name.endswith(".xml")
                )
            parts: list[str] = []
            for name in names:
                try:
                    root = ET.fromstring(archive.read(name))
                except KeyError:
                    continue
                texts = [
                    node.text
                    for node in root.iter()
                    if node.text and node.tag.endswith("}t")
                ]
                joined = "\n".join(texts).strip()
                if joined:
                    parts.append(joined)
            return "\n\n".join(parts).strip()
    except Exception:
        return ""


def _load_document_bytes(storage_path: str) -> bytes:
    if not storage_path or str(storage_path).startswith("failed://"):
        raise FileNotFoundError("El documento no tiene un fichero almacenado")
    path = Path(storage_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(storage_path)
    return path.read_bytes()


ProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]


async def _emit(on_progress: ProgressCallback | None, **event: Any) -> None:
    if on_progress is None:
        return
    await on_progress(event)


async def _delete_document_chunks(db: AsyncSession, document_id: str) -> None:
    await db.execute(
        text(
            """
            DELETE FROM embeddings
            WHERE chunk_id IN (
                SELECT id FROM chunks WHERE document_id = :document_id
            )
            """
        ),
        {"document_id": document_id},
    )
    await db.execute(
        text("DELETE FROM chunks WHERE document_id = :document_id"),
        {"document_id": document_id},
    )
    await db.commit()


async def ensure_document_chunks(
    db: AsyncSession,
    document_id: str,
    on_progress: ProgressCallback | None = None,
    force: bool = False,
) -> int:
    """Crea fragmentos si el documento aún no tiene ninguno."""
    count_q = await db.execute(
        text("SELECT COUNT(*) FROM chunks WHERE document_id = :document_id"),
        {"document_id": document_id},
    )
    existing = int(count_q.scalar() or 0)
    if existing > 0:
        if not force:
            sample_q = await db.execute(
                text(
                    """
                    SELECT content
                    FROM chunks
                    WHERE document_id = :document_id
                    ORDER BY position ASC
                    LIMIT 12
                    """
                ),
                {"document_id": document_id},
            )
            samples = [str(row[0] or "") for row in sample_q.all()]
            if not corpus_looks_corrupted(samples):
                await _emit(
                    on_progress,
                    stage="chunk",
                    percent=35,
                    chunks=existing,
                    total=existing,
                    message=f"{existing} fragmentos ya existían.",
                )
                return existing
        await _emit(
            on_progress,
            stage="extract",
            percent=18,
            message=(
                "Reextrayendo texto con OCR…"
                if force
                else "Los fragmentos guardados son ilegibles; se extrae de nuevo con OCR…"
            ),
        )
        await _delete_document_chunks(db, document_id)

    doc_q = await db.execute(
        text(
            """
            SELECT id, filename, mime_type, storage_path
            FROM documents
            WHERE id = :document_id
            """
        ),
        {"document_id": document_id},
    )
    document = doc_q.mappings().first()
    if document is None:
        raise ValueError("Documento no encontrado")

    await _emit(
        on_progress,
        stage="extract",
        percent=20,
        message="Leyendo el archivo…",
    )
    raw = await asyncio.to_thread(
        _load_document_bytes, str(document["storage_path"] or "")
    )
    filename = str(document["filename"] or "")
    extracting = (
        "Transcribiendo el vídeo…"
        if is_video_file(filename, document.get("mime_type"))
        else "Extrayendo texto (OCR en páginas ilegibles)…"
    )
    await _emit(
        on_progress,
        stage="extract",
        percent=24,
        message=extracting,
    )
    body = await asyncio.to_thread(
        extract_index_text,
        filename,
        raw,
        document.get("mime_type"),
    )
    parts = [
        part
        for part in split_into_chunks(body)
        if is_readable_text(part, min_chars=24)
    ]
    if not parts:
        raise ValueError(
            "No se pudo extraer texto del documento para indexar. "
            "Comprueba que el fichero no esté vacío."
        )

    await _emit(
        on_progress,
        stage="chunk",
        percent=32,
        chunks=len(parts),
        total=len(parts),
        message=f"Creando {len(parts)} fragmentos…",
    )
    doc_uuid = UUID(str(document_id))
    db.add_all(
        [
            Chunk(
                id=uuid4(),
                document_id=doc_uuid,
                position=position,
                headline=part.split("\n", 1)[0][:200],
                summary=part[:280],
                content=part,
            )
            for position, part in enumerate(parts)
        ]
    )
    await db.commit()
    await _emit(
        on_progress,
        stage="chunk",
        percent=38,
        chunks=len(parts),
        total=len(parts),
        message=f"{len(parts)} fragmentos listos.",
    )
    return len(parts)


async def record_reindex_on_job(
    db: AsyncSession,
    *,
    document_id: str,
    tenant_id: str | None,
    models: list[str],
    result: dict,
) -> None:
    chunk_count = int(result.get("chunks") or 0)
    per_model = result.get("models") or {}
    primary = next((item for item in models if item and str(item).strip()), None)
    for model, stats in per_model.items():
        if (stats or {}).get("indexed") or (stats or {}).get("skipped"):
            primary = model
    errors = [
        str(stats.get("error"))
        for stats in per_model.values()
        if isinstance(stats, dict) and stats.get("error")
    ]
    indexed_any = any(
        int((stats or {}).get("indexed") or 0) > 0
        or int((stats or {}).get("skipped") or 0) > 0
        for stats in per_model.values()
    )
    failed = chunk_count <= 0 or not indexed_any
    status = "failed" if failed else "completed"
    error_message = None
    if failed:
        error_message = (errors[0] if errors else None) or (
            "No se generaron fragmentos para indexar."
            if chunk_count <= 0
            else "No se pudieron generar embeddings."
        )
    params = {
        "status": status,
        "model": (primary or "")[:100] or None,
        "chunks": chunk_count,
        "error": error_message,
        "document_id": document_id,
        "tenant_id": tenant_id,
        "job_id": str(uuid4()),
    }
    updated = await db.execute(
        text(
            """
            UPDATE processing_jobs
            SET
                status = :status,
                embedding_model = :model,
                chunks_generated = :chunks,
                error_message = :error,
                finished_at = NOW(),
                started_at = COALESCE(started_at, NOW())
            WHERE id = (
                SELECT id FROM processing_jobs
                WHERE document_id = :document_id
                ORDER BY started_at DESC NULLS LAST
                LIMIT 1
            )
            """
        ),
        params,
    )
    if not updated.rowcount:
        await db.execute(
            text(
                """
                INSERT INTO processing_jobs (
                    id, tenant_id, document_id, status,
                    started_at, finished_at, error_message,
                    chunks_generated, embedding_model
                )
                VALUES (
                    :job_id, :tenant_id, :document_id, :status,
                    NOW(), NOW(), :error, :chunks, :model
                )
                """
            ),
            params,
        )
    await db.commit()


async def ensure_multi_embedding_schema(db: AsyncSession) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    for statement in ENSURE_MULTI_EMBEDDING_SQL:
        await db.execute(text(statement))
    await db.commit()
    _SCHEMA_READY = True


async def list_indexed_models(db: AsyncSession) -> list[str]:
    result = await db.execute(
        text(
            """
            SELECT DISTINCT model
            FROM public.embeddings
            WHERE model IS NOT NULL AND btrim(model) <> ''
            ORDER BY model
            """
        )
    )
    return [str(row[0]) for row in result.all() if row[0]]


def _http_client() -> httpx.Client:
    global _HTTP
    if _HTTP is None or _HTTP.is_closed:
        _HTTP = httpx.Client(
            timeout=httpx.Timeout(180.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=4, max_connections=8),
        )
    return _HTTP


def _embed_batch(model: str, texts: list[str]) -> list[list[float]]:
    """Un solo POST nativo a Ollama; keep-alive reutiliza el socket."""
    response = _http_client().post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": model, "input": texts, "keep_alive": "24h"},
    )
    if response.status_code >= 400:
        client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)
        fallback = client.embeddings.create(model=model, input=texts)
        by_index = {item.index: item.embedding for item in fallback.data}
        return [pad_vector(by_index[i]) for i in range(len(texts))]
    payload = response.json()
    vectors = payload.get("embeddings") or payload.get("embedding") or []
    if vectors and isinstance(vectors[0], (int, float)):
        vectors = [vectors]
    if len(vectors) != len(texts):
        raise RuntimeError(
            f"Ollama devolvió {len(vectors)} vectores para {len(texts)} textos"
        )
    return [pad_vector(list(item)) for item in vectors]


def _ensure_model_available(model: str) -> None:
    """Descarga bajo demanda un embedding del catálogo si Ollama no lo tiene."""
    with httpx.Client(timeout=httpx.Timeout(900.0, connect=10.0)) as client:
        response = client.get(f"{OLLAMA_URL}/api/tags")
        response.raise_for_status()
        installed = {
            str(item.get("name") or item.get("model") or "")
            for item in response.json().get("models", [])
        }
        base_names = {name.removesuffix(":latest") for name in installed}
        if model in installed or model.removesuffix(":latest") in base_names:
            return
        pulled = client.post(
            f"{OLLAMA_URL}/api/pull",
            json={"name": model, "stream": False},
        )
        pulled.raise_for_status()


async def reindex_embeddings(
    db: AsyncSession,
    *,
    tenant_id: str,
    models: list[str],
    knowledge_base_id: str | None = None,
    document_id: str | None = None,
    on_progress: ProgressCallback | None = None,
    force_rebuild: bool = False,
) -> dict:
    await ensure_multi_embedding_schema(db)
    wanted = [item.strip() for item in models if item and item.strip()]
    if not wanted:
        wanted = [DEFAULT_EMBEDDING_MODEL]
    if document_id:
        await ensure_document_chunks(
            db,
            document_id,
            on_progress=on_progress,
            force=force_rebuild,
        )

    clauses = ["d.tenant_id = :tenant_id"]
    params: dict = {"tenant_id": tenant_id}
    if knowledge_base_id:
        clauses.append("d.knowledge_base_id = :knowledge_base_id")
        params["knowledge_base_id"] = knowledge_base_id
    if document_id:
        clauses.append("c.document_id = :document_id")
        params["document_id"] = document_id

    chunks_q = await db.execute(
        text(
            f"""
            SELECT c.id, c.headline, c.summary, c.content
            FROM public.chunks c
            JOIN public.documents d ON d.id = c.document_id
            WHERE {' AND '.join(clauses)}
            ORDER BY c.position ASC
            """
        ),
        params,
    )
    chunks = [dict(row) for row in chunks_q.mappings().all()]
    per_model: dict[str, dict] = {}

    for model in wanted:
        existing_q = await db.execute(
            text(
                f"""
                SELECT e.chunk_id
                FROM public.embeddings e
                JOIN public.chunks c ON c.id = e.chunk_id
                JOIN public.documents d ON d.id = c.document_id
                WHERE e.model = :model AND {' AND '.join(clauses)}
                """
            ),
            {**params, "model": model},
        )
        already = {str(row[0]) for row in existing_q.all()}
        pending = [row for row in chunks if str(row["id"]) not in already]
        indexed = 0
        failed = 0
        error = None
        if pending:
            await _emit(
                on_progress,
                stage="embed",
                percent=40,
                total=len(chunks),
                embedded=len(already),
                chunks=len(chunks),
                message=f"Preparando modelo {model}…",
            )
            try:
                await asyncio.to_thread(_ensure_model_available, model)
            except Exception as exc:
                per_model[model] = {
                    "indexed": 0,
                    "skipped": len(already),
                    "pending": len(pending),
                    "failed": len(pending),
                    "error": f"No se pudo preparar {model} en Ollama: {exc}"[:400],
                }
                continue
        for start in range(0, len(pending), BATCH_SIZE):
            batch = pending[start : start + BATCH_SIZE]
            done = len(already) + indexed
            denom = max(len(chunks), 1)
            await _emit(
                on_progress,
                stage="embed",
                percent=40 + int(55 * (done / denom)),
                embedded=done,
                total=len(chunks),
                chunks=len(chunks),
                message=f"Embeddings {done}/{len(chunks)}…",
            )
            texts = [
                embedding_payload(
                    item.get("headline"), item.get("summary"), item.get("content")
                )
                for item in batch
            ]
            try:
                vectors = await asyncio.to_thread(_embed_batch, model, texts)
            except Exception as exc:
                failed += len(batch)
                error = str(exc)[:400]
                continue
            db.add_all(
                [
                    Embedding(
                        id=uuid4(),
                        chunk_id=UUID(str(item["id"])),
                        model=model,
                        vector=vector,
                    )
                    for item, vector in zip(batch, vectors)
                ]
            )
            indexed += len(batch)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                indexed = max(0, indexed - len(batch))
                failed += len(batch)
                continue
            done = len(already) + indexed
            await _emit(
                on_progress,
                stage="embed",
                percent=40 + int(55 * (done / max(len(chunks), 1))),
                embedded=done,
                total=len(chunks),
                chunks=len(chunks),
                message=f"Embeddings {done}/{len(chunks)}…",
            )
        per_model[model] = {
            "indexed": indexed,
            "skipped": len(already),
            "pending": len(pending),
            "failed": failed,
            "error": error,
        }

    return {
        "chunks": len(chunks),
        "models": per_model,
        "note": (
            "Cada modelo queda en su propio espacio vectorial. "
            "Comparar MRR/nDCG entre embeddings es válido tras este reindexado."
        ),
    }
