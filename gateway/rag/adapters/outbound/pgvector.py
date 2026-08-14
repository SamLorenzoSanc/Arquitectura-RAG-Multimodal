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
        index_dimensions = min(HNSW_INDEX_DIMENSIONS, len(raw_embedding))
        query_index = raw_embedding[:index_dimensions]
        approximate_distance = _vector_distance(
            func.subvector(Embedding.vector, 1, index_dimensions).cast(
                Vector(index_dimensions)
            ),
            query_index,
            distance_metric,
        )
        exact_distance = _vector_distance(
            Embedding.vector, raw_embedding, distance_metric
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
                        "type": document.mime_type,
                        "distance": float(distance),
                        "retrieval_source": "dense",
                        "embedding_latency_ms": t_emb * 1000,
                        "dense_latency_ms": (time.time() - t0) * 1000,
                    },
                )
            )
        return results
