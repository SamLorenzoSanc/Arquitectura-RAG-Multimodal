from __future__ import annotations

from rag.application.retrieve import invalidate_retrieval_cache
from rag.domain.ports import LexicalIndexPort


class IngestDocument:
    """Tras indexar un documento, reconstruye BM25 e invalida caches de retrieval."""

    def __init__(self, lexical: LexicalIndexPort):
        self.lexical = lexical

    async def execute(self, tenant_id: str) -> None:
        self.lexical.invalidate(tenant_id)
        await self.lexical.rebuild(tenant_id)
        invalidate_retrieval_cache(tenant_id)
