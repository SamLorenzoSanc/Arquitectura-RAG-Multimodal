from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from rag.domain.entities import RetrievedChunk


@runtime_checkable
class EmbeddingPort(Protocol):
    async def embed(self, text: str) -> list[float]: ...


@runtime_checkable
class LlmPort(Protocol):
    async def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
    ) -> str: ...

    async def parse(
        self, model: str, messages: list[dict[str, str]], response_format: Any
    ) -> Any: ...


@runtime_checkable
class ChunkRepository(Protocol):
    async def retrieve_dense(
        self,
        question: str,
        tenant_id: str,
        collections: list[str] | None,
        *,
        k: int,
        distance_metric: str = "cosine",
        embedding_model: str | None = None,
    ) -> list[RetrievedChunk]: ...


@runtime_checkable
class LexicalIndexPort(Protocol):
    async def retrieve(
        self,
        question: str,
        tenant_id: str,
        collections: list[str] | None,
        *,
        k: int,
    ) -> list[RetrievedChunk]: ...

    async def rebuild(self, tenant_id: str) -> None: ...

    def invalidate(self, tenant_id: str | None = None) -> None: ...


@runtime_checkable
class RerankerPort(Protocol):
    def rerank(
        self, question: str, chunks: list[RetrievedChunk]
    ) -> list[RetrievedChunk]: ...
