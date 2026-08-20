from __future__ import annotations

import os
import time

from pgvector.sqlalchemy import Vector
from sqlalchemy import func, select

from models.chunk import Chunk
from models.document import Document
from models.embedding import Embedding
from rag.adapters.outbound.scope import is_uuid, organization_tenant_ids
from rag.domain.entities import RetrievedChunk
from rag.domain.ports import EmbeddingPort
from services.database import AsyncSessionLocal

HNSW_INDEX_DIMENSIONS = int(os.getenv("HNSW_INDEX_DIMENSIONS", "2000"))
STORAGE_VECTOR_DIM = int(os.getenv("PGVECTOR_STORAGE_DIM", "4096"))


def pad_query_vector(values: list[float], dim: int = STORAGE_VECTOR_DIM) -> list[float]:
    vector = list(values or [])
    if len(vector) >= dim:
        return vector[:dim]
    return vector + [0.0] * (dim - len(vector))


def prepare_query_vectors(
    raw_embedding: list[float],
    *,
    storage_dim: int = STORAGE_VECTOR_DIM,
    index_dim: int = HNSW_INDEX_DIMENSIONS,
) -> tuple[list[float], list[float], int]:
    """Alinea la consulta Nomic (768) con la columna pgvector (4096) y el HNSW."""
    padded = pad_query_vector(list(raw_embedding or []), storage_dim)
    index_dimensions = min(max(index_dim, 1), storage_dim)
    return padded, padded[:index_dimensions], index_dimensions


def _vector_distance(column, query, metric: str = "cosine"):
    metric = (metric or "cosine").lower()
    if metric in {"euclidean", "l2"}:
        return column.l2_distance(query)
    if metric in {"manhattan", "l1"}:
        if hasattr(column, "l1_distance"):
            return column.l1_distance(query)
        return column.l2_distance(query)
    if metric in {"inner_product", "ip"}:
        return column.max_inner_product(query)
    return column.cosine_distance(query)


class PgvectorChunkRepository:
    def __init__(self, embeddings: EmbeddingPort, embedding_model: str | None = None):
        self.embeddings = embeddings
        self.embedding_model = embedding_model

    async def retrieve_dense(
        self,
        question: str,
        tenant_id: str,
        collections: list[str] | None,
        *,
        k: int,
        distance_metric: str = "cosine",
        embedding_model: str | None = None,
    ) -> list[RetrievedChunk]:
        t0 = time.time()
        raw_embedding = await self.embeddings.embed(question)
        t_emb = time.time() - t0
        padded, query_index, index_dimensions = prepare_query_vectors(raw_embedding)
        approximate_distance = _vector_distance(
            func.subvector(Embedding.vector, 1, index_dimensions).cast(
                Vector(index_dimensions)
            ),
            query_index,
            distance_metric,
        )
        exact_distance = _vector_distance(
            Embedding.vector, padded, distance_metric
        )
        stmt = (
            select(Chunk, Document, exact_distance.label("distance"))
            .join(Embedding, Embedding.chunk_id == Chunk.id)
            .join(Document, Document.id == Chunk.document_id)
        )
        if is_uuid(tenant_id):
            stmt = stmt.where(
                Document.tenant_id.in_(organization_tenant_ids(tenant_id))
            )
        else:
            stmt = stmt.where(Document.tenant_id == tenant_id)
        if collections:
            stmt = stmt.where(Document.knowledge_base_id.in_(collections))
        model = embedding_model or self.embedding_model
        if model:
            stmt = stmt.where(Embedding.model == model)
        stmt = stmt.order_by(approximate_distance).limit(k)

        async with AsyncSessionLocal() as session:
            rows = (await session.execute(stmt)).all()
            if not rows:
                return []

        results: list[RetrievedChunk] = []
        for chunk, document, distance in rows:
            results.append(
                RetrievedChunk(
                    page_content="\n\n".join(
                        part
                        for part in [chunk.headline, chunk.summary, chunk.content]
                        if part
                    ).strip(),
                    metadata={
                        "chunk_id": str(chunk.id),
                        "document_id": str(document.id),
                        "tenant_id": str(document.tenant_id),
                        "knowledge_base_id": str(document.knowledge_base_id),
                        "source": document.filename,
                        "headline": chunk.headline or "",
                        "type": document.mime_type,
                        "distance": float(distance),
                        "retrieval_source": "dense",
                        "embedding_latency_ms": t_emb * 1000,
                        "dense_latency_ms": (time.time() - t0) * 1000,
                    },
                )
            )
        return results
