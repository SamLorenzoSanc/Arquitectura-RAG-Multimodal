from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievedChunk:
    """Fragmento recuperado. El dominio no depende de Pydantic ni de SQLAlchemy."""

    page_content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalQuery:
    question: str
    tenant_id: str = "global"
    collections: list[str] | None = None
    distance_metric: str = "cosine"
    use_reranking: bool = False
    use_query_rewrite: bool = False
    evaluation_mode: bool = False


@dataclass
class RetrievalBundle:
    chunks: list[RetrievedChunk]
    rewritten_query: str
    dense_original: list[RetrievedChunk]
    dense_rewritten: list[RetrievedChunk]
    bm25_original: list[RetrievedChunk]
    bm25_rewritten: list[RetrievedChunk]
    candidates: list[RetrievedChunk]
    retrieval: dict[str, Any]
    cache_scope: str | None = None
