from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from threading import Lock

from rag.domain.entities import RetrievalBundle, RetrievalQuery, RetrievedChunk
from rag.domain.fusion import rrf_fusion
from rag.domain.lexicon import expand_agro_query, should_rewrite_query
from rag.domain.ports import (
    ChunkRepository,
    LexicalIndexPort,
    LlmPort,
    RerankerPort,
)

_RETRIEVAL_CACHE: OrderedDict[str, tuple[float, RetrievalBundle]] = OrderedDict()
_RETRIEVAL_CACHE_TTL = 120
_RETRIEVAL_CACHE_MAX_SIZE = 256
_RETRIEVAL_CACHE_LOCK = Lock()


def _cache_key(
    query: RetrievalQuery, strategy: str, rerank: bool, rewrite: bool
) -> str:
    cols = ",".join(sorted(query.collections or []))
    raw = (
        f"{query.tenant_id}|{query.question.strip()}|"
        f"s={strategy}|rr={int(rerank)}|rw={int(rewrite)}|"
        f"d={query.distance_metric}|{cols}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def invalidate_retrieval_cache(tenant_id: str | None = None) -> int:
    with _RETRIEVAL_CACHE_LOCK:
        if tenant_id is None:
            count = len(_RETRIEVAL_CACHE)
            _RETRIEVAL_CACHE.clear()
            return count
        prefix = f"{tenant_id}|"
        keys = [
            key
            for key, (_, bundle) in _RETRIEVAL_CACHE.items()
            if (bundle.cache_scope or "").startswith(prefix)
        ]
        for key in keys:
            _RETRIEVAL_CACHE.pop(key, None)
        return len(keys)


class HybridRetrieve:
    """Caso de uso: Dense + BM25 + RRF (+ rerank opcional)."""

    def __init__(
        self,
        chunks: ChunkRepository,
        lexical: LexicalIndexPort,
        llm: LlmPort,
        reranker: RerankerPort,
        *,
        retrieval_k: int = 10,
        bm25_k: int = 10,
        rrf_k: int = 60,
        candidate_k: int = 15,
        final_k: int = 3,
        chat_model: str = "llama3.2:latest",
        embedding_model: str | None = None,
        reranker_model: str = "BAAI/bge-reranker-v2-m3",
    ):
        self.chunks = chunks
        self.lexical = lexical
        self.llm = llm
        self.reranker = reranker
        self.retrieval_k = retrieval_k
        self.bm25_k = bm25_k
        self.rrf_k = rrf_k
        self.candidate_k = candidate_k
        self.final_k = final_k
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.reranker_model = reranker_model

    async def execute(self, query: RetrievalQuery) -> RetrievalBundle:
        question = " ".join(query.question.strip().split())
        strategy = (query.retrieval_strategy or "hybrid").strip().lower()
        valid_strategies = {
            "hybrid",
            "dense",
            "bm25",
            "hybrid_rrf",
            "hybrid_rrf_rerank",
            "hybrid_expansion_rrf",
            "hybrid_expansion_rrf_rerank",
        }
        if strategy not in valid_strategies:
            raise ValueError(f"Estrategia de recuperación no soportada: {strategy}")
        explicit_rerank = strategy.endswith("_rerank")
        explicit_expansion = "_expansion_" in strategy
        legacy_mode = strategy == "hybrid"
        do_rerank = explicit_rerank or (legacy_mode and bool(query.use_reranking))
        allow_rewrite = explicit_expansion or (
            legacy_mode and bool(query.use_query_rewrite)
        )
        expand_lexical = explicit_expansion or legacy_mode
        metric = (query.distance_metric or "cosine").lower()

        cache_key = _cache_key(query, strategy, do_rerank, allow_rewrite)
        now = time.time()
        if not query.evaluation_mode:
            with _RETRIEVAL_CACHE_LOCK:
                cached = _RETRIEVAL_CACHE.get(cache_key)
                if cached and (now - cached[0]) < _RETRIEVAL_CACHE_TTL:
                    _RETRIEVAL_CACHE.move_to_end(cache_key)
                    return cached[1]

        empty = self._empty_bundle(question)
        if not question:
            return empty

        t0 = time.time()
        if strategy in {"dense", "bm25"}:
            return await self._execute_single_retriever(
                query,
                question=question,
                strategy=strategy,
                metric=metric,
                cache_key=cache_key,
                started_at=t0,
            )

        t_rewrite = time.time()
        rewrite_required = allow_rewrite and should_rewrite_query(question)
        if rewrite_required:
            rewritten = await self._rewrite(question)
            rewritten = " ".join(rewritten.strip().split()) or question
        else:
            rewritten = question
        rewrite_latency_ms = (time.time() - t_rewrite) * 1000

        t_retrieval = time.time()
        if rewritten == question:
            dense_original, bm25_original = await self._parallel_pair(
                question,
                query.tenant_id,
                query.collections,
                metric,
                expand_lexical=expand_lexical,
            )
            dense_rewritten = dense_original
            bm25_rewritten = bm25_original
        else:
            dense_original, dense_rewritten, bm25_original, bm25_rewritten = (
                await self._parallel_four(
                    question,
                    rewritten,
                    query.tenant_id,
                    query.collections,
                    metric,
                    expand_lexical=expand_lexical,
                )
            )
        retrieval_latency_ms = (time.time() - t_retrieval) * 1000

        t_rrf = time.time()
        candidates = rrf_fusion(
            dense_original,
            dense_rewritten,
            bm25_original,
            bm25_rewritten,
            rrf_k=self.rrf_k,
            candidate_k=self.candidate_k,
        )
        rrf_latency_ms = (time.time() - t_rrf) * 1000

        t_rerank = time.time()
        ranked = (
            self.reranker.rerank(question, candidates) if do_rerank else candidates
        )
        rerank_latency_ms = (time.time() - t_rerank) * 1000
        final_chunks = ranked[: self.final_k]
        elapsed = time.time() - t0

        bundle = RetrievalBundle(
            chunks=final_chunks,
            rewritten_query=rewritten,
            dense_original=dense_original,
            dense_rewritten=dense_rewritten,
            bm25_original=bm25_original,
            bm25_rewritten=bm25_rewritten,
            candidates=candidates,
            cache_scope=(
                f"{query.tenant_id}|{','.join(sorted(query.collections or []))}"
            ),
            retrieval={
                "original_query": question,
                "rewritten_query": rewritten,
                "strategy": strategy,
                "retrieved_chunks": len(dense_original),
                "rewritten_chunks": len(dense_rewritten),
                "merged_chunks": len(candidates),
                "dense_original_chunks": len(dense_original),
                "dense_rewritten_chunks": len(dense_rewritten),
                "bm25_original_chunks": len(bm25_original),
                "bm25_rewritten_chunks": len(bm25_rewritten),
                "candidate_chunks": len(candidates),
                "final_chunks": len(final_chunks),
                "retrieval_k": self.retrieval_k,
                "bm25_k": self.bm25_k,
                "candidate_k": self.candidate_k,
                "final_k": self.final_k,
                "rrf_k": self.rrf_k,
                "reranking": do_rerank,
                "reranker": self.reranker_model if do_rerank else None,
                "query_rewriting": rewrite_required,
                "parallel_retrieval": True,
                "timings_ms": {
                    "rewrite": rewrite_latency_ms,
                    "retrieval_parallel": retrieval_latency_ms,
                    "rrf": rrf_latency_ms,
                    "reranking": rerank_latency_ms,
                    "total_retrieval": elapsed * 1000,
                    "embedding": max(
                        (
                            chunk.metadata.get("embedding_latency_ms", 0.0)
                            for chunk in dense_original
                        ),
                        default=0.0,
                    ),
                    "dense": max(
                        (
                            chunk.metadata.get("dense_latency_ms", 0.0)
                            for chunk in dense_original
                        ),
                        default=0.0,
                    ),
                    "bm25": max(
                        (
                            chunk.metadata.get("bm25_latency_ms", 0.0)
                            for chunk in bm25_original
                        ),
                        default=0.0,
                    ),
                },
            },
        )
        if not query.evaluation_mode:
            with _RETRIEVAL_CACHE_LOCK:
                _RETRIEVAL_CACHE[cache_key] = (time.time(), bundle)
                _RETRIEVAL_CACHE.move_to_end(cache_key)
                while len(_RETRIEVAL_CACHE) > _RETRIEVAL_CACHE_MAX_SIZE:
                    _RETRIEVAL_CACHE.popitem(last=False)
        return bundle

    async def _execute_single_retriever(
        self,
        query: RetrievalQuery,
        *,
        question: str,
        strategy: str,
        metric: str,
        cache_key: str,
        started_at: float,
    ) -> RetrievalBundle:
        if strategy == "dense":
            chunks = await self.chunks.retrieve_dense(
                question,
                query.tenant_id,
                query.collections,
                k=self.retrieval_k,
                distance_metric=metric,
                embedding_model=self.embedding_model,
            )
            dense, lexical = chunks, []
        else:
            chunks = await self.lexical.retrieve(
                question,
                query.tenant_id,
                query.collections,
                k=self.bm25_k,
            )
            dense, lexical = [], chunks
        elapsed_ms = (time.time() - started_at) * 1000
        final_chunks = chunks[: self.final_k]
        bundle = RetrievalBundle(
            chunks=final_chunks,
            rewritten_query=question,
            dense_original=dense,
            dense_rewritten=[],
            bm25_original=lexical,
            bm25_rewritten=[],
            candidates=chunks,
            cache_scope=(
                f"{query.tenant_id}|{','.join(sorted(query.collections or []))}"
            ),
            retrieval={
                "original_query": question,
                "rewritten_query": question,
                "strategy": strategy,
                "retrieved_chunks": len(chunks),
                "merged_chunks": len(chunks),
                "candidate_chunks": len(chunks),
                "final_chunks": len(final_chunks),
                "retrieval_k": self.retrieval_k,
                "bm25_k": self.bm25_k,
                "candidate_k": self.candidate_k,
                "final_k": self.final_k,
                "rrf_k": None,
                "reranking": False,
                "query_rewriting": False,
                "parallel_retrieval": False,
                "timings_ms": {"total_retrieval": elapsed_ms},
            },
        )
        if not query.evaluation_mode:
            with _RETRIEVAL_CACHE_LOCK:
                _RETRIEVAL_CACHE[cache_key] = (time.time(), bundle)
                _RETRIEVAL_CACHE.move_to_end(cache_key)
                while len(_RETRIEVAL_CACHE) > _RETRIEVAL_CACHE_MAX_SIZE:
                    _RETRIEVAL_CACHE.popitem(last=False)
        return bundle

    async def _rewrite(self, question: str) -> str:
        prompt = (
            "Respuesta en español.\nReescribe únicamente la consulta.\n"
            f"Pregunta:\n{question}"
        )
        return await self.llm.complete(
            self.chat_model, [{"role": "system", "content": prompt}]
        )

    async def _parallel_pair(
        self,
        question: str,
        tenant_id: str,
        collections: list[str] | None,
        metric: str,
        *,
        expand_lexical: bool,
    ) -> tuple[list[RetrievedChunk], list[RetrievedChunk]]:
        import asyncio

        return await asyncio.gather(
            self.chunks.retrieve_dense(
                question,
                tenant_id,
                collections,
                k=self.retrieval_k,
                distance_metric=metric,
                embedding_model=self.embedding_model,
            ),
            self.lexical.retrieve(
                expand_agro_query(question) if expand_lexical else question,
                tenant_id,
                collections,
                k=self.bm25_k,
            ),
        )

    async def _parallel_four(
        self,
        question: str,
        rewritten: str,
        tenant_id: str,
        collections: list[str] | None,
        metric: str,
        *,
        expand_lexical: bool,
    ):
        import asyncio

        return await asyncio.gather(
            self.chunks.retrieve_dense(
                question,
                tenant_id,
                collections,
                k=self.retrieval_k,
                distance_metric=metric,
                embedding_model=self.embedding_model,
            ),
            self.chunks.retrieve_dense(
                rewritten,
                tenant_id,
                collections,
                k=self.retrieval_k,
                distance_metric=metric,
                embedding_model=self.embedding_model,
            ),
            self.lexical.retrieve(
                expand_agro_query(question) if expand_lexical else question,
                tenant_id,
                collections,
                k=self.bm25_k,
            ),
            self.lexical.retrieve(
                expand_agro_query(rewritten) if expand_lexical else rewritten,
                tenant_id,
                collections,
                k=self.bm25_k,
            ),
        )

    def _empty_bundle(self, question: str) -> RetrievalBundle:
        return RetrievalBundle(
            chunks=[],
            rewritten_query=question,
            dense_original=[],
            dense_rewritten=[],
            bm25_original=[],
            bm25_rewritten=[],
            candidates=[],
            retrieval={
                "original_query": question,
                "rewritten_query": question,
                "retrieved_chunks": 0,
                "rewritten_chunks": 0,
                "merged_chunks": 0,
                "candidate_chunks": 0,
                "final_chunks": 0,
                "reranking": False,
                "reranker": None,
            },
        )
