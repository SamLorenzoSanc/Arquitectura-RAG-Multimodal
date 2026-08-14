"""Reindexado de chunks con varios modelos de embedding (un vector por par chunk×modelo)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from uuid import UUID, uuid4

from openai import OpenAI
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.chunk import Chunk
from models.embedding import Embedding
from services.rag_service import DEFAULT_EMBEDDING_MODEL

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")
VECTOR_DIM = 4096
BATCH_SIZE = 8
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_INDEX_CHARS = 400_000
MAX_PDF_PAGES = 80

EMBEDDING_CATALOG = [
    {
        "id": "qwen3-embedding:latest",
        "label": "Qwen3 Embedding",
        "why": "Modelo por defecto del RAG; buen español técnico.",
    },
    {
        "id": "nomic-embed-text",
        "label": "Nomic Embed Text",
        "why": "Embedding ligero, útil como baseline de comparación.",
    },
    {
        "id": "mxbai-embed-large",
        "label": "mixedbread large",
        "why": "Embedding denso de mayor capacidad semántica.",
    },
    {
        "id": "bge-m3",
        "label": "BGE-M3",
        "why": "Multilingüe; contraste frente a Qwen3 en normativa.",
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
        from services.question_extraction import _extract_pdf_text

        return _extract_pdf_text(
            content, max_pages=MAX_PDF_PAGES, max_chars=MAX_INDEX_CHARS
        )

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


async def ensure_document_chunks(db: AsyncSession, document_id: str) -> int:
    """Crea fragmentos si el documento aún no tiene ninguno (la subida no los genera)."""
    count_q = await db.execute(
        text("SELECT COUNT(*) FROM chunks WHERE document_id = :document_id"),
        {"document_id": document_id},
    )
    existing = int(count_q.scalar() or 0)
    if existing > 0:
        return existing

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

    raw = _load_document_bytes(str(document["storage_path"] or ""))
    body = extract_index_text(
        str(document["filename"] or ""),
        raw,
        document.get("mime_type"),
    )
    parts = split_into_chunks(body)
    if not parts:
        raise ValueError(
            "No se pudo extraer texto del documento para indexar. "
            "Comprueba que el fichero no esté vacío o escaneado sin OCR."
        )

    doc_uuid = UUID(str(document_id))
    for position, part in enumerate(parts):
        headline = part.split("\n", 1)[0][:200]
        db.add(
            Chunk(
                id=uuid4(),
                document_id=doc_uuid,
                position=position,
                headline=headline,
                summary=part[:280],
                content=part,
            )
        )
    await db.commit()
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
    for statement in ENSURE_MULTI_EMBEDDING_SQL:
        await db.execute(text(statement))
    await db.commit()


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


def _embed_batch(model: str, texts: list[str]) -> list[list[float]]:
    client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)
    response = client.embeddings.create(model=model, input=texts)
    by_index = {item.index: item.embedding for item in response.data}
    return [pad_vector(by_index[i]) for i in range(len(texts))]


async def reindex_embeddings(
    db: AsyncSession,
    *,
    tenant_id: str,
    models: list[str],
    knowledge_base_id: str | None = None,
    document_id: str | None = None,
) -> dict:
    await ensure_multi_embedding_schema(db)
    wanted = [item.strip() for item in models if item and item.strip()]
    if not wanted:
        wanted = [DEFAULT_EMBEDDING_MODEL]
    if document_id:
        await ensure_document_chunks(db, document_id)

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
        for start in range(0, len(pending), BATCH_SIZE):
            batch = pending[start : start + BATCH_SIZE]
            texts = [
                chunk_text(item.get("headline"), item.get("summary"), item.get("content"))
                or " "
                for item in batch
            ]
            try:
                vectors = _embed_batch(model, texts)
            except Exception as exc:
                failed += len(batch)
                error = str(exc)[:400]
                continue
            for item, vector in zip(batch, vectors):
                db.add(
                    Embedding(
                        id=uuid4(),
                        chunk_id=UUID(str(item["id"])),
                        model=model,
                        vector=vector,
                    )
                )
                indexed += 1
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                indexed = max(0, indexed - len(batch))
                failed += len(batch)
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
