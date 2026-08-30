"""Indexador por lotes: modelos activos, hash de cambio y estados pending/indexing/indexed/failed."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any
from uuid import uuid4

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import AsyncSessionLocal
from services.embedding_reindex import reindex_embeddings
from services.rag_service import DEFAULT_EMBEDDING_MODEL, RAGService

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = max(1, int(os.getenv("EMBEDDING_BATCH_SIZE", "20")))
DEFAULT_LEASE_MINUTES = max(1, int(os.getenv("EMBEDDING_LEASE_MINUTES", "15")))
DEFAULT_INTERVAL_SECONDS = max(5, int(os.getenv("EMBEDDING_INDEXER_INTERVAL", "20")))
INDEXER_ENABLED = os.getenv("EMBEDDING_INDEXER_ENABLED", "true").lower() in {
    "1",
    "true",
    "yes",
}

ENSURE_INDEXER_SQL = (
    """
    CREATE TABLE IF NOT EXISTS public.embedding_model (
        id UUID PRIMARY KEY,
        slug TEXT NOT NULL UNIQUE,
        runtime_model_id TEXT NOT NULL,
        display_name TEXT NOT NULL,
        dimensions INTEGER NOT NULL DEFAULT 768,
        max_input_tokens INTEGER,
        chunk_max_tokens INTEGER,
        chunk_overlap INTEGER,
        status TEXT NOT NULL DEFAULT 'inactive'
            CHECK (status IN ('active', 'inactive')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS public.embedding_index_state (
        id UUID PRIMARY KEY,
        document_id UUID NOT NULL
            REFERENCES public.documents(id) ON DELETE CASCADE,
        embedding_model_id UUID NOT NULL
            REFERENCES public.embedding_model(id) ON DELETE CASCADE,
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'indexing', 'indexed', 'failed')),
        source_hash TEXT,
        attempts INTEGER NOT NULL DEFAULT 0,
        error TEXT,
        leased_until TIMESTAMPTZ,
        finished_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (document_id, embedding_model_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_embedding_index_state_status
        ON public.embedding_index_state (status, updated_at)
    """,
    """
    INSERT INTO public.embedding_model (
        id, slug, runtime_model_id, display_name, dimensions, status
    ) VALUES
        (
            'a0e1b2c3-0001-4000-8000-000000000001',
            'nomic-embed-text',
            'nomic-embed-text',
            'Nomic Embed Text',
            768,
            'active'
        ),
        (
            'a0e1b2c3-0002-4000-8000-000000000002',
            'qwen3-embedding',
            'qwen3-embedding:latest',
            'Qwen3 Embedding',
            1024,
            'inactive'
        ),
        (
            'a0e1b2c3-0003-4000-8000-000000000003',
            'mxbai-embed-large',
            'mxbai-embed-large',
            'mixedbread large',
            1024,
            'inactive'
        ),
        (
            'a0e1b2c3-0004-4000-8000-000000000004',
            'bge-m3',
            'bge-m3',
            'BGE-M3',
            1024,
            'inactive'
        )
    ON CONFLICT (slug) DO NOTHING
    """,
)

_SCHEMA_READY = False


async def ensure_indexer_schema(db: AsyncSession) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    for statement in ENSURE_INDEXER_SQL:
        await db.execute(text(statement))
    await db.commit()
    _SCHEMA_READY = True


async def list_catalog(db: AsyncSession) -> list[dict[str, Any]]:
    await ensure_indexer_schema(db)
    rows = (
        await db.execute(
            text(
                """
                SELECT id::text, slug, runtime_model_id, display_name, dimensions,
                       status, max_input_tokens, chunk_max_tokens, chunk_overlap
                FROM public.embedding_model
                ORDER BY status DESC, display_name
                """
            )
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def _nomic_model_id(db: AsyncSession) -> str | None:
    row = await db.execute(
        text(
            """
            SELECT id
            FROM public.embedding_model
            WHERE runtime_model_id = :default
               OR slug = :default
            ORDER BY created_at
            LIMIT 1
            """
        ),
        {"default": DEFAULT_EMBEDDING_MODEL},
    )
    value = row.scalar()
    return str(value) if value else None


async def get_active_runtime_model(db: AsyncSession) -> str:
    """Modelo del corpus: el único active, o Nomic si hay varios o ninguno."""
    await ensure_indexer_schema(db)
    rows = (
        await db.execute(
            text(
                """
                SELECT runtime_model_id
                FROM public.embedding_model
                WHERE status = 'active'
                ORDER BY display_name
                """
            )
        )
    ).all()
    if len(rows) == 1 and rows[0][0]:
        return str(rows[0][0])
    return DEFAULT_EMBEDDING_MODEL


async def get_corpus_model(db: AsyncSession) -> dict[str, Any] | None:
    await ensure_indexer_schema(db)
    runtime = await get_active_runtime_model(db)
    row = (
        await db.execute(
            text(
                """
                SELECT id::text, slug, runtime_model_id, display_name, dimensions, status
                FROM public.embedding_model
                WHERE runtime_model_id = :runtime
                LIMIT 1
                """
            ),
            {"runtime": runtime},
        )
    ).mappings().first()
    return dict(row) if row else None


async def ingest_model_ids(db: AsyncSession) -> list[str]:
    """Al subir: siempre Nomic. Si el corpus está en un único modelo distinto, también ese."""
    await ensure_indexer_schema(db)
    nomic_id = await _nomic_model_id(db)
    ids: list[str] = []
    if nomic_id:
        ids.append(nomic_id)
    active = (
        await db.execute(
            text("SELECT id FROM public.embedding_model WHERE status = 'active'")
        )
    ).all()
    active_ids = [str(row[0]) for row in active if row[0]]
    if len(active_ids) == 1 and active_ids[0] not in ids:
        ids.append(active_ids[0])
    return ids or active_ids[:1]


async def apply_model_to_corpus(db: AsyncSession, model_id: str) -> dict[str, Any]:
    """Deja un solo modelo active y encola todos los documentos para reindexarlo."""
    await ensure_indexer_schema(db)
    row = (
        await db.execute(
            text(
                """
                SELECT id::text, slug, runtime_model_id, display_name, dimensions, status
                FROM public.embedding_model
                WHERE id = :id
                """
            ),
            {"id": model_id},
        )
    ).mappings().first()
    if row is None:
        raise ValueError("Modelo no encontrado")
    await db.execute(
        text(
            """
            UPDATE public.embedding_model
            SET status = 'inactive', updated_at = NOW()
            """
        )
    )
    await db.execute(
        text(
            """
            UPDATE public.embedding_model
            SET status = 'active', updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": model_id},
    )
    queued = await enqueue_all_documents_for_model(db, model_id)
    await db.commit()
    tenants = (
        await db.execute(text("SELECT DISTINCT tenant_id::text FROM public.documents"))
    ).all()
    for (tenant_id,) in tenants:
        if tenant_id:
            try:
                RAGService.invalidate_retrieval_cache(str(tenant_id))
            except Exception:
                logger.exception("No se pudo invalidar la caché de %s", tenant_id)
    return {**dict(row), "status": "active", "queued": queued}


async def set_model_status(db: AsyncSession, model_id: str, status: str) -> dict[str, Any]:
    await ensure_indexer_schema(db)
    value = "active" if status in {"active", "activado", "enabled", "true", "1"} else "inactive"
    if value == "active":
        return await apply_model_to_corpus(db, model_id)
    row = (
        await db.execute(
            text(
                """
                UPDATE public.embedding_model
                SET status = :status, updated_at = NOW()
                WHERE id = :id
                RETURNING id::text, slug, runtime_model_id, display_name, dimensions, status
                """
            ),
            {"id": model_id, "status": value},
        )
    ).mappings().first()
    if row is None:
        raise ValueError("Modelo no encontrado")
    await db.commit()
    return dict(row)


async def enqueue_document(
    db: AsyncSession,
    *,
    document_id: str,
    source_hash: str | None,
    force: bool = False,
) -> int:
    """Crea o pasa a pending una fila: Nomic (defecto) y, si aplica, el modelo del corpus."""
    model_ids = await ingest_model_ids(db)
    if not model_ids:
        return 0
    queued = 0
    for model_id in model_ids:
        await db.execute(
            text(
                """
                INSERT INTO public.embedding_index_state (
                    id, document_id, embedding_model_id, status, source_hash,
                    attempts, error, leased_until, finished_at, updated_at
                ) VALUES (
                    :id, :document_id, :model_id, 'pending', :source_hash,
                    0, NULL, NULL, NULL, NOW()
                )
                ON CONFLICT (document_id, embedding_model_id) DO UPDATE
                SET
                    status = CASE
                        WHEN :force
                          OR public.embedding_index_state.status <> 'indexed'
                          OR public.embedding_index_state.source_hash IS DISTINCT FROM EXCLUDED.source_hash
                        THEN 'pending'
                        ELSE public.embedding_index_state.status
                    END,
                    source_hash = EXCLUDED.source_hash,
                    error = CASE
                        WHEN :force
                          OR public.embedding_index_state.source_hash IS DISTINCT FROM EXCLUDED.source_hash
                        THEN NULL
                        ELSE public.embedding_index_state.error
                    END,
                    leased_until = NULL,
                    updated_at = NOW()
                """
            ),
            {
                "id": str(uuid4()),
                "document_id": document_id,
                "model_id": str(model_id),
                "source_hash": source_hash,
                "force": force,
            },
        )
        queued += 1
    return queued


async def enqueue_all_documents_for_model(db: AsyncSession, model_id: str) -> int:
    result = await db.execute(
        text(
            """
            INSERT INTO public.embedding_index_state (
                id, document_id, embedding_model_id, status, source_hash, updated_at
            )
            SELECT gen_random_uuid(), d.id, :model_id, 'pending', d.file_hash, NOW()
            FROM public.documents d
            ON CONFLICT (document_id, embedding_model_id) DO UPDATE
            SET
                status = CASE
                    WHEN public.embedding_index_state.status = 'indexed'
                     AND public.embedding_index_state.source_hash
                         IS NOT DISTINCT FROM EXCLUDED.source_hash
                    THEN public.embedding_index_state.status
                    ELSE 'pending'
                END,
                error = CASE
                    WHEN public.embedding_index_state.status = 'indexed'
                     AND public.embedding_index_state.source_hash
                         IS NOT DISTINCT FROM EXCLUDED.source_hash
                    THEN public.embedding_index_state.error
                    ELSE NULL
                END,
                leased_until = CASE
                    WHEN public.embedding_index_state.status = 'indexed'
                     AND public.embedding_index_state.source_hash
                         IS NOT DISTINCT FROM EXCLUDED.source_hash
                    THEN public.embedding_index_state.leased_until
                    ELSE NULL
                END,
                updated_at = NOW()
            """
        ),
        {"model_id": model_id},
    )
    return int(result.rowcount or 0)


async def retry_state(db: AsyncSession, state_id: str) -> dict[str, Any] | None:
    await ensure_indexer_schema(db)
    row = (
        await db.execute(
            text(
                """
                UPDATE public.embedding_index_state
                SET status = 'pending', error = NULL, leased_until = NULL, updated_at = NOW()
                WHERE id = :id
                RETURNING id::text, document_id::text, status, attempts
                """
            ),
            {"id": state_id},
        )
    ).mappings().first()
    await db.commit()
    return dict(row) if row else None


async def list_document_states(db: AsyncSession, document_id: str) -> list[dict[str, Any]]:
    await ensure_indexer_schema(db)
    rows = (
        await db.execute(
            text(
                """
                SELECT
                    s.id::text AS id,
                    s.document_id::text AS document_id,
                    s.status,
                    s.source_hash,
                    s.attempts,
                    s.error,
                    s.finished_at,
                    s.updated_at,
                    m.id::text AS model_id,
                    m.slug,
                    m.display_name,
                    m.runtime_model_id,
                    m.status AS model_status
                FROM public.embedding_index_state s
                JOIN public.embedding_model m ON m.id = s.embedding_model_id
                WHERE s.document_id = :document_id
                ORDER BY m.display_name
                """
            ),
            {"document_id": document_id},
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def list_states_for_documents(
    db: AsyncSession, document_ids: list[str]
) -> dict[str, list[dict[str, Any]]]:
    if not document_ids:
        return {}
    await ensure_indexer_schema(db)
    rows = (
        await db.execute(
            text(
                """
                SELECT
                    s.id::text AS id,
                    s.document_id::text AS document_id,
                    s.status,
                    s.attempts,
                    s.error,
                    s.updated_at,
                    m.slug,
                    m.display_name,
                    m.runtime_model_id
                FROM public.embedding_index_state s
                JOIN public.embedding_model m ON m.id = s.embedding_model_id
                WHERE s.document_id IN :ids
                ORDER BY m.display_name
                """
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": document_ids},
        )
    ).mappings().all()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["document_id"]), []).append(dict(row))
    return grouped


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _search_clause(search: str | None) -> tuple[str, dict[str, Any]]:
    query = (search or "").strip()
    if not query:
        return "", {}
    return (
        " AND (d.filename ILIKE :q OR COALESCE(d.title, '') ILIKE :q)",
        {"q": f"%{query}%"},
    )


async def summarize_index(
    db: AsyncSession, knowledge_base_ids: list[str]
) -> dict[str, int]:
    empty = {
        "total": 0,
        "indexed": 0,
        "pending": 0,
        "indexing": 0,
        "failed": 0,
        "none": 0,
    }
    if not knowledge_base_ids:
        return empty
    await ensure_indexer_schema(db)
    status_rows = (
        await db.execute(
            text(
                """
                SELECT s.status, COUNT(*)::int AS n
                FROM public.embedding_index_state s
                JOIN public.documents d ON d.id = s.document_id
                WHERE d.knowledge_base_id IN :ids
                GROUP BY s.status
                """
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": knowledge_base_ids},
        )
    ).all()
    for status, count in status_rows:
        key = str(status)
        if key in empty:
            empty[key] = int(count)
            empty["total"] += int(count)
    none = await db.execute(
        text(
            """
            SELECT COUNT(*)::int
            FROM public.documents d
            WHERE d.knowledge_base_id IN :ids
              AND NOT EXISTS (
                  SELECT 1 FROM public.embedding_index_state s
                  WHERE s.document_id = d.id
              )
            """
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": knowledge_base_ids},
    )
    empty["none"] = int(none.scalar() or 0)
    return empty


async def list_index_tasks(
    db: AsyncSession,
    *,
    knowledge_base_ids: list[str],
    status: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    await ensure_indexer_schema(db)
    counts = await summarize_index(db, knowledge_base_ids)
    if not knowledge_base_ids:
        return {"counts": counts, "items": [], "total": 0, "limit": limit, "offset": offset}
    extra, params = _search_clause(search)
    count_bind: dict[str, Any] = {"ids": knowledge_base_ids, **params}
    list_bind: dict[str, Any] = {
        "ids": knowledge_base_ids,
        "limit": limit,
        "offset": offset,
        **params,
    }
    if status == "none":
        count_sql = f"""
            SELECT COUNT(*)::int
            FROM public.documents d
            WHERE d.knowledge_base_id IN :ids
              AND NOT EXISTS (
                  SELECT 1 FROM public.embedding_index_state s
                  WHERE s.document_id = d.id
              )
            {extra}
        """
        list_sql = f"""
            SELECT
                NULL::text AS id,
                d.id::text AS document_id,
                d.filename,
                d.title,
                d.knowledge_base_id::text AS knowledge_base_id,
                'none' AS status,
                0 AS attempts,
                NULL::text AS error,
                d.uploaded_at AS updated_at,
                NULL::text AS slug,
                NULL::text AS display_name,
                NULL::text AS runtime_model_id
            FROM public.documents d
            WHERE d.knowledge_base_id IN :ids
              AND NOT EXISTS (
                  SELECT 1 FROM public.embedding_index_state s
                  WHERE s.document_id = d.id
              )
            {extra}
            ORDER BY d.uploaded_at DESC
            LIMIT :limit OFFSET :offset
        """
    else:
        status_sql = ""
        if status and status != "all":
            status_sql = " AND s.status = :status"
            count_bind["status"] = status
            list_bind["status"] = status
        count_sql = f"""
            SELECT COUNT(*)::int
            FROM public.embedding_index_state s
            JOIN public.documents d ON d.id = s.document_id
            WHERE d.knowledge_base_id IN :ids
            {status_sql}
            {extra}
        """
        list_sql = f"""
            SELECT
                s.id::text AS id,
                s.document_id::text AS document_id,
                d.filename,
                d.title,
                d.knowledge_base_id::text AS knowledge_base_id,
                s.status,
                s.attempts,
                s.error,
                s.updated_at,
                m.slug,
                m.display_name,
                m.runtime_model_id
            FROM public.embedding_index_state s
            JOIN public.documents d ON d.id = s.document_id
            JOIN public.embedding_model m ON m.id = s.embedding_model_id
            WHERE d.knowledge_base_id IN :ids
            {status_sql}
            {extra}
            ORDER BY
                CASE s.status
                    WHEN 'failed' THEN 0
                    WHEN 'indexing' THEN 1
                    WHEN 'pending' THEN 2
                    ELSE 4
                END,
                s.updated_at ASC
            LIMIT :limit OFFSET :offset
        """
    total = int(
        (
            await db.execute(
                text(count_sql).bindparams(bindparam("ids", expanding=True)),
                count_bind,
            )
        ).scalar()
        or 0
    )
    rows = (
        await db.execute(
            text(list_sql).bindparams(bindparam("ids", expanding=True)),
            list_bind,
        )
    ).mappings().all()
    items = []
    for row in rows:
        item = dict(row)
        item["updated_at"] = _iso(item.get("updated_at"))
        items.append(item)
    return {
        "counts": counts,
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def retry_states(db: AsyncSession, state_ids: list[str]) -> int:
    if not state_ids:
        return 0
    await ensure_indexer_schema(db)
    result = await db.execute(
        text(
            """
            UPDATE public.embedding_index_state
            SET status = 'pending', error = NULL, leased_until = NULL, updated_at = NOW()
            WHERE id IN :ids
              AND status <> 'indexing'
            """
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": state_ids},
    )
    await db.commit()
    return int(result.rowcount or 0)


async def retry_filtered(
    db: AsyncSession,
    *,
    knowledge_base_ids: list[str],
    status: str | None,
    search: str | None = None,
) -> int:
    await ensure_indexer_schema(db)
    if not knowledge_base_ids:
        return 0
    if status == "none":
        extra, params = _search_clause(search)
        result = await db.execute(
            text(
                f"""
                INSERT INTO public.embedding_index_state (
                    id, document_id, embedding_model_id, status, source_hash, updated_at
                )
                SELECT gen_random_uuid(), d.id, m.id, 'pending', d.file_hash, NOW()
                FROM public.documents d
                CROSS JOIN public.embedding_model m
                WHERE d.knowledge_base_id IN :ids
                  AND m.status = 'active'
                  AND NOT EXISTS (
                      SELECT 1 FROM public.embedding_index_state s
                      WHERE s.document_id = d.id AND s.embedding_model_id = m.id
                  )
                {extra}
                """
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": knowledge_base_ids, **params},
        )
        await db.commit()
        return int(result.rowcount or 0)
    extra, params = _search_clause(search)
    status_sql = " AND s.status <> 'indexing'"
    bind: dict[str, Any] = {"ids": knowledge_base_ids, **params}
    if status and status not in {"all", "none"}:
        status_sql = " AND s.status = :status AND s.status <> 'indexing'"
        bind["status"] = status
    result = await db.execute(
        text(
            f"""
            UPDATE public.embedding_index_state AS s
            SET status = 'pending', error = NULL, leased_until = NULL, updated_at = NOW()
            FROM public.documents d
            WHERE s.document_id = d.id
              AND d.knowledge_base_id IN :ids
            {status_sql}
            {extra}
            """
        ).bindparams(bindparam("ids", expanding=True)),
        bind,
    )
    await db.commit()
    return int(result.rowcount or 0)


async def _claim_batch(
    db: AsyncSession, *, batch_size: int, lease_minutes: int
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            text(
                """
                SELECT
                    s.id,
                    s.document_id,
                    s.embedding_model_id,
                    m.runtime_model_id,
                    m.slug,
                    d.file_hash,
                    d.tenant_id::text AS tenant_id,
                    d.knowledge_base_id::text AS knowledge_base_id
                FROM public.embedding_index_state s
                JOIN public.embedding_model m ON m.id = s.embedding_model_id
                JOIN public.documents d ON d.id = s.document_id
                WHERE m.status = 'active'
                  AND EXISTS (
                    SELECT 1 FROM public.chunks c WHERE c.document_id = s.document_id
                  )
                  AND (
                    s.status IN ('pending', 'failed')
                    OR (s.status = 'indexing' AND (s.leased_until IS NULL OR s.leased_until < NOW()))
                    OR (s.status = 'indexed' AND s.source_hash IS DISTINCT FROM d.file_hash)
                  )
                ORDER BY s.updated_at ASC
                LIMIT :batch
                FOR UPDATE OF s SKIP LOCKED
                """
            ),
            {"batch": batch_size},
        )
    ).mappings().all()
    claimed = [dict(row) for row in rows]
    if not claimed:
        return []
    ids = [str(item["id"]) for item in claimed]
    await db.execute(
        text(
            """
            UPDATE public.embedding_index_state
            SET status = 'indexing',
                leased_until = NOW() + make_interval(mins => :lease),
                attempts = attempts + 1,
                error = NULL,
                updated_at = NOW()
            WHERE id IN :ids
            """
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": ids, "lease": lease_minutes},
    )
    await db.commit()
    return claimed


async def mark_indexed_for_runtime(
    db: AsyncSession,
    *,
    document_id: str,
    runtime_model_id: str,
    source_hash: str | None,
) -> None:
    """Marca indexed el par documento×modelo tras una ingesta síncrona (p. ej. nomic)."""
    await db.execute(
        text(
            """
            UPDATE public.embedding_index_state AS s
            SET status = 'indexed',
                source_hash = :source_hash,
                error = NULL,
                leased_until = NULL,
                finished_at = NOW(),
                updated_at = NOW()
            FROM public.embedding_model AS m
            WHERE s.embedding_model_id = m.id
              AND s.document_id = :document_id
              AND m.runtime_model_id = :runtime
            """
        ),
        {
            "document_id": document_id,
            "runtime": runtime_model_id,
            "source_hash": source_hash,
        },
    )


async def _mark_indexed(db: AsyncSession, state_id: str, source_hash: str | None) -> None:
    await db.execute(
        text(
            """
            UPDATE public.embedding_index_state
            SET status = 'indexed',
                source_hash = :source_hash,
                error = NULL,
                leased_until = NULL,
                finished_at = NOW(),
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": state_id, "source_hash": source_hash},
    )
    await db.commit()


async def _mark_failed(db: AsyncSession, state_id: str, error: str) -> None:
    await db.execute(
        text(
            """
            UPDATE public.embedding_index_state
            SET status = 'failed',
                error = :error,
                leased_until = NULL,
                finished_at = NOW(),
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": state_id, "error": error[:2000]},
    )
    await db.commit()


async def _drop_model_vectors(db: AsyncSession, document_id: str, runtime_model: str) -> None:
    await db.execute(
        text(
            """
            DELETE FROM public.embeddings
            WHERE model = :model
              AND chunk_id IN (
                  SELECT id FROM public.chunks WHERE document_id = :document_id
              )
            """
        ),
        {"model": runtime_model, "document_id": document_id},
    )
    await db.commit()


async def index_one(db: AsyncSession, row: dict[str, Any]) -> None:
    document_id = str(row["document_id"])
    runtime = str(row["runtime_model_id"])
    tenant_id = str(row["tenant_id"])
    kb_id = str(row["knowledge_base_id"]) if row.get("knowledge_base_id") else None
    source_hash = str(row["file_hash"]) if row.get("file_hash") else None
    await _drop_model_vectors(db, document_id, runtime)
    result = await reindex_embeddings(
        db,
        tenant_id=tenant_id,
        models=[runtime],
        knowledge_base_id=kb_id,
        document_id=document_id,
        force_rebuild=False,
    )
    model_stats = (result.get("models") or {}).get(runtime) or {}
    if model_stats.get("error") and not model_stats.get("indexed"):
        raise RuntimeError(str(model_stats["error"]))
    await _mark_indexed(db, str(row["id"]), source_hash)


async def run_indexer(
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    lease_minutes: int = DEFAULT_LEASE_MINUTES,
) -> dict[str, int]:
    processed = 0
    failed = 0
    tenants: set[str] = set()
    async with AsyncSessionLocal() as db:
        await ensure_indexer_schema(db)
        batch = await _claim_batch(db, batch_size=batch_size, lease_minutes=lease_minutes)
        for row in batch:
            try:
                await index_one(db, row)
                processed += 1
                if row.get("tenant_id"):
                    tenants.add(str(row["tenant_id"]))
            except Exception as exc:
                failed += 1
                logger.exception("Indexación fallida %s", row.get("id"))
                try:
                    await _mark_failed(db, str(row["id"]), str(exc))
                except Exception:
                    logger.exception("No se pudo marcar failed %s", row.get("id"))
    for tenant_id in tenants:
        try:
            RAGService.invalidate_retrieval_cache(tenant_id)
        except Exception:
            logger.exception("No se pudo invalidar la caché de %s", tenant_id)
    summary = {
        "claimed": processed + failed,
        "processed": processed,
        "failed": failed,
        "batch_size": batch_size,
    }
    if processed or failed:
        logger.info("[EMBEDDING_INDEXER] done %s", summary)
    return summary


async def indexer_loop() -> None:
    logger.info(
        "[EMBEDDING_INDEXER] start interval=%ss batch=%s lease=%smin",
        DEFAULT_INTERVAL_SECONDS,
        DEFAULT_BATCH_SIZE,
        DEFAULT_LEASE_MINUTES,
    )
    while True:
        try:
            await run_indexer()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("[EMBEDDING_INDEXER] fatal")
        await asyncio.sleep(DEFAULT_INTERVAL_SECONDS)


def schedule_indexer() -> asyncio.Task | None:
    if not INDEXER_ENABLED:
        logger.info("[EMBEDDING_INDEXER] desactivado")
        return None
    return asyncio.create_task(indexer_loop(), name="agrops-embedding-indexer")
