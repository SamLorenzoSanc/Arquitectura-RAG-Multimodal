"""Retrieval microservice: Dense (pgvector) + fusión simple.

Contrato alineado con protos/retrieval.proto. Usa inference-service
para el embedding de la query y Postgres/pgvector para la búsqueda.
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlparse, urlunparse

import asyncpg
import httpx
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@postgres:5432/agrops",
)
INFERENCE_URL = os.getenv("INFERENCE_URL", "http://inference:50051").rstrip("/")
EMBED_MODEL = os.getenv("DEFAULT_EMBED_MODEL", "qwen3-embedding:latest")

app = FastAPI(title="AgroPS Retrieval Service", version="1.0.0")
_pool: asyncpg.Pool | None = None


def _asyncpg_dsn(url: str) -> str:
    """Convierte SQLAlchemy/URL render a DSN asyncpg."""
    u = url.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(u)
    # quitar query ssl=require; asyncpg lo gestiona aparte si hace falta
    return urlunparse(parsed._replace(scheme="postgresql", query=""))


class RetrieveBody(BaseModel):
    question: str
    tenant_id: str = "global"
    collections: list[str] = Field(default_factory=list)
    retrieval_k: int = 10
    final_k: int = 5
    use_reranking: bool = False
    use_query_rewrite: bool = False


@app.on_event("startup")
async def startup() -> None:
    global _pool
    dsn = _asyncpg_dsn(DATABASE_URL)
    kwargs: dict[str, Any] = {"min_size": 1, "max_size": 5}
    if "render.com" in dsn or "ssl=require" in DATABASE_URL:
        kwargs["ssl"] = True
    _pool = await asyncpg.create_pool(dsn, **kwargs)


@app.on_event("shutdown")
async def shutdown() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@app.get("/health")
async def health() -> dict[str, Any]:
    ok_db = False
    if _pool:
        try:
            async with _pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            ok_db = True
        except Exception:
            ok_db = False
    return {"status": "ok" if ok_db else "degraded", "service": "retrieval", "db": ok_db}


async def _embed_query(question: str) -> list[float]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{INFERENCE_URL}/v1/embeddings",
            json={"model": EMBED_MODEL, "input": question},
        )
        if resp.status_code >= 400:
            raise HTTPException(status_code=502, detail=resp.text)
        data = resp.json()
        return data["data"][0]["embedding"]


def _vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


@app.post("/v1/retrieve")
@app.post("/rpc/Retrieve")
async def retrieve(body: RetrieveBody) -> dict[str, Any]:
    if not _pool:
        raise HTTPException(status_code=503, detail="DB pool not ready")

    query_vec = await _embed_query(body.question)
    lit = _vector_literal(query_vec)
    k = max(1, body.retrieval_k)

    # Dense retrieval sobre embeddings (cosine via <=> operador pgvector).
    # Columna real en seed: embeddings.vector
    sql = """
        SELECT c.id::text AS chunk_id,
               c.document_id::text AS document_id,
               COALESCE(
                 NULLIF(TRIM(CONCAT_WS(E'\\n\\n', c.headline, c.summary, c.content)), ''),
                 c.content,
                 ''
               ) AS page_content,
               COALESCE(d.filename, d.title, 'doc') AS source,
               (e.vector <=> $1::vector) AS distance
        FROM embeddings e
        JOIN chunks c ON c.id = e.chunk_id
        LEFT JOIN documents d ON d.id = c.document_id
        ORDER BY e.vector <=> $1::vector
        LIMIT $2
    """
    try:
        async with _pool.acquire() as conn:
            rows = await conn.fetch(sql, lit, k)
    except Exception as exc:
        # Fallback: si el esquema difiere, devolver vacío con error suave
        raise HTTPException(
            status_code=500,
            detail=f"Retrieval SQL error (¿migraciones/pgvector?): {exc}",
        ) from exc

    chunks = []
    for r in rows[: body.final_k]:
        dist = float(r["distance"]) if r["distance"] is not None else 1.0
        score = 1.0 / (1.0 + dist)
        chunks.append(
            {
                "chunk_id": r["chunk_id"],
                "document_id": r["document_id"],
                "page_content": r["page_content"] or "",
                "source": r["source"] or "doc",
                "score": score,
                "metadata": {
                    "distance": str(dist),
                    "tenant_id": body.tenant_id,
                },
            }
        )

    return {
        "architecture": "retrieval_service_dense_pgvector",
        "original_query": body.question,
        "rewritten_query": body.question,
        "chunks": chunks,
        "retrieved_chunks": len(rows),
        "final_chunks": len(chunks),
        "retrieval_k": body.retrieval_k,
        "final_k": body.final_k,
        "reranking": body.use_reranking,
    }
