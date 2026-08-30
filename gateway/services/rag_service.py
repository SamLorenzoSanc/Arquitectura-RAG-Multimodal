from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel
from sqlalchemy import select
from tenacity import wait_exponential

from models.chunk import Chunk
from models.document import Document
from models.embedding import Embedding
from rag.adapters.mapping import bundle_to_dict, from_result, to_results
from rag.adapters.outbound.ollama import (
    OLLAMA_API_KEY,
    OLLAMA_BASE_URL,
    RAG_CHAT_MAX_TOKENS,
    RAG_KEEP_ALIVE,
    RAG_MAX_TOKENS,
    RAG_NUM_CTX,
    RAG_TEMPERATURE,
)
from rag.application.answer import build_prompt as _build_prompt
from rag.application.answer import related_questions_knn
from rag.application.evaluate import (
    RetrievalEval,
    calculate_dcg,
    calculate_mrr,
    calculate_ndcg,
)
from rag.application.prompts import SYSTEM_PROMPT
from rag.application.retrieve import invalidate_retrieval_cache
from rag.composition import build_rag_container
from rag.domain.entities import RetrievalQuery, RetrievedChunk
from rag.domain.fusion import rrf_fusion as domain_rrf
from rag.domain.lexicon import expand_agro_query as domain_expand
from rag.domain.related import generate_related_questions
from schemas.chat import Result
from services.database import AsyncSessionLocal

load_dotenv(override=True)
WAIT_POLICY = wait_exponential(multiplier=1, min=10, max=240)

HNSW_INDEX_DIMENSIONS = int(os.getenv("HNSW_INDEX_DIMENSIONS", "2000"))
DEFAULT_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "nomic-embed-text")
DEFAULT_CHAT_MODEL = os.getenv("RAG_GENERATION_MODEL", "llama3.2:latest")
RAG_USE_RERANKER = os.getenv("RAG_USE_RERANKER", "false").lower() in {
    "1",
    "true",
    "yes",
}
RAG_USE_QUERY_REWRITE = os.getenv("RAG_USE_QUERY_REWRITE", "false").lower() in {
    "1",
    "true",
    "yes",
}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


DEFAULT_RETRIEVAL_K = _env_int("RAG_RETRIEVAL_K", 8)
DEFAULT_BM25_K = _env_int("RAG_BM25_K", 8)
DEFAULT_CANDIDATE_K = _env_int("RAG_CANDIDATE_K", 12)
DEFAULT_FINAL_K = _env_int("RAG_FINAL_K", 3)
DEFAULT_RRF_K = _env_int("RAG_RRF_K", 60)
EVAL_TOP_K = _env_int("RAG_EVAL_TOP_K", 3)


def rag_runtime_config(*, embedding_model: str | None = None) -> dict[str, Any]:
    """Contrato visible: chat y evaluación deben mostrar estos valores."""
    return {
        "generation_model": DEFAULT_CHAT_MODEL,
        "embedding_model": embedding_model or DEFAULT_EMBEDDING_MODEL,
        "temperature": RAG_TEMPERATURE,
        "chunk_size_chars": _env_int("RAG_CHUNK_SIZE", 1400),
        "chunk_overlap_chars": _env_int("RAG_CHUNK_OVERLAP", 120),
        "retrieval_k": DEFAULT_RETRIEVAL_K,
        "bm25_k": DEFAULT_BM25_K,
        "rrf_k": DEFAULT_RRF_K,
        "candidate_k": DEFAULT_CANDIDATE_K,
        "final_k": DEFAULT_FINAL_K,
        "eval_top_k": EVAL_TOP_K,
        "chat_max_tokens": RAG_CHAT_MAX_TOKENS,
        "num_ctx": RAG_NUM_CTX,
        "use_reranker": RAG_USE_RERANKER,
        "use_query_rewrite": RAG_USE_QUERY_REWRITE,
        "note": (
            "Chat rápido: final_k + RAG_CHAT_MAX_TOKENS + hybrid_rrf/dense. "
            "La evaluación IR usa eval_top_k=3."
        ),
    }


def chat_service_ks(
    retrieval_k: int | None = None,
    final_k: int | None = None,
) -> dict[str, int]:
    """k del chat sin inflar artificialmente BM25/candidatos."""
    rk = max(1, int(retrieval_k if retrieval_k is not None else DEFAULT_RETRIEVAL_K))
    fk = max(1, int(final_k if final_k is not None else DEFAULT_FINAL_K))
    return {
        "retrieval_k": rk,
        "bm25_k": max(1, min(DEFAULT_BM25_K, rk)),
        "candidate_k": max(fk, min(DEFAULT_CANDIDATE_K, max(rk, fk * 2))),
        "final_k": fk,
    }


class DatasetEvaluationRequest(BaseModel):
    model_name: str = "llama3.2"
    embedding_model: str = "nomic-embed-text"
    top_k: int = 5
    retrieval_k: int = 10
    bm25_k: int = 10
    rrf_k: int = 60
    candidate_k: int = 15
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_batch_size: int = 16


class DatasetEvaluationResponse(BaseModel):
    run_id: int
    model_name: str
    embedding_model: str
    dataset_size: int
    normal_questions: int
    different_info_questions: int
    out_of_knowledge_questions: int
    recall_1: float
    recall_k: float
    mrr: float
    false_positives: int
    failures: int
    duration_ms: float
    status: str
    parameters: dict


class EvaluationHistoryItem(BaseModel):
    id: int
    created_at: str
    model_name: str
    embedding_model: str
    dataset_size: int
    top_k: int
    recall_1: float
    recall_k: float
    mrr: float
    false_positives: int
    failures: int
    duration_ms: float
    status: str


class EvaluationResultItem(BaseModel):
    id: int
    dataset_id: int
    question: str
    expected_chunk_id: str | None
    retrieved_chunk_ids: list[str]
    retrieved_scores: list[float]
    expected_rank: int | None
    hit_at_1: bool
    hit_at_k: bool
    reciprocal_rank: float
    false_positive: bool
    failure: bool
    flag_different_info: bool
    flag_out_of_knowledge: bool
    retrieval_latency_ms: float | None


def _coerce_related_chunk(item: Any) -> RetrievedChunk:
    if isinstance(item, RetrievedChunk):
        return item
    if isinstance(item, Result):
        return from_result(item)
    if isinstance(item, dict):
        return RetrievedChunk(
            page_content=item.get("page_content") or "",
            metadata=dict(item.get("metadata") or {}),
        )
    return RetrievedChunk(
        page_content=getattr(item, "page_content", "") or "",
        metadata=dict(getattr(item, "metadata", None) or {}),
    )


class RAGService:
    """Fachada hexagonal: las rutas FastAPI siguen usando esta API."""

    SYSTEM_PROMPT = SYSTEM_PROMPT
    DEFAULT_RERANKER = "BAAI/bge-reranker-v2-m3"

    def __init__(
        self,
        model: str = DEFAULT_CHAT_MODEL,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        retrieval_k: int = DEFAULT_RETRIEVAL_K,
        bm25_k: int = DEFAULT_BM25_K,
        rrf_k: int = 60,
        candidate_k: int = DEFAULT_CANDIDATE_K,
        final_k: int = DEFAULT_FINAL_K,
        reranker_model: str = DEFAULT_RERANKER,
        reranker_batch_size: int = 16,
        bm25_index_dir: str | None = None,
    ):
        self.model = model
        self.embedding_model = embedding_model
        self.retrieval_k = retrieval_k
        self.bm25_k = bm25_k
        self.rrf_k = rrf_k
        self.candidate_k = candidate_k
        self.final_k = final_k
        self.reranker_model = reranker_model
        self.reranker_batch_size = reranker_batch_size
        self.wait = WAIT_POLICY
        self._container = build_rag_container(
            model=model,
            embedding_model=embedding_model,
            retrieval_k=retrieval_k,
            bm25_k=bm25_k,
            rrf_k=rrf_k,
            candidate_k=candidate_k,
            final_k=final_k,
            reranker_model=reranker_model,
            reranker_batch_size=reranker_batch_size,
            bm25_index_dir=bm25_index_dir,
        )
        self.client = self._container.llm.client
        self.bm25_index_dir = self._container.lexical.index_dir

    @staticmethod
    def expand_agro_query(question: str) -> str:
        return domain_expand(question)

    async def retrieve(
        self,
        question: str,
        tenant_id: str,
        collections: list[str] | None = None,
        distance_metric: str = "cosine",
    ) -> list[Result]:
        chunks = await self._container.chunks.retrieve_dense(
            question,
            tenant_id,
            collections,
            k=self.retrieval_k,
            distance_metric=distance_metric,
            embedding_model=self.embedding_model,
        )
        return to_results(chunks)

    async def retrieve_bm25(
        self,
        question: str,
        tenant_id: str,
        collections: list[str] | None = None,
    ) -> list[Result]:
        chunks = await self._container.lexical.retrieve(
            question, tenant_id, collections, k=self.bm25_k
        )
        return to_results(chunks)

    def rrf_fusion(
        self,
        dense_original: list[Result],
        dense_rewritten: list[Result],
        bm25_original: list[Result],
        bm25_rewritten: list[Result],
    ) -> list[Result]:
        fused = domain_rrf(
            [from_result(c) for c in dense_original],
            [from_result(c) for c in dense_rewritten],
            [from_result(c) for c in bm25_original],
            [from_result(c) for c in bm25_rewritten],
            rrf_k=self.rrf_k,
            candidate_k=self.candidate_k,
        )
        return to_results(fused)

    def cross_encoder_rerank(self, question: str, chunks: list[Result]) -> list[Result]:
        ranked = self._container.reranker.rerank(
            question, [from_result(c) for c in chunks]
        )
        return to_results(ranked)

    async def fetch_context(
        self,
        question: str,
        tenant_id: str = "global",
        collections: list[str] | None = None,
        evaluation_mode: bool = False,
        use_reranking: bool | None = None,
        use_query_rewrite: bool | None = None,
        distance_metric: str = "cosine",
        retrieval_strategy: str = "hybrid",
    ):
        do_rerank = RAG_USE_RERANKER if use_reranking is None else bool(use_reranking)
        allow_rewrite = (
            RAG_USE_QUERY_REWRITE
            if use_query_rewrite is None
            else bool(use_query_rewrite)
        )
        bundle = await self._container.retrieve.execute(
            RetrievalQuery(
                question=question,
                tenant_id=tenant_id,
                collections=collections,
                distance_metric=distance_metric,
                retrieval_strategy=retrieval_strategy,
                use_reranking=do_rerank,
                use_query_rewrite=allow_rewrite,
                evaluation_mode=evaluation_mode,
            )
        )
        return bundle_to_dict(bundle)

    async def fetch_context_simple(
        self, question, tenant_id="global", collections=None
    ):
        return await self.fetch_context(question, tenant_id, collections)

    def build_prompt(self, question: str, history: list, chunks: list[Result]):
        return _build_prompt(question, history, [from_result(c) for c in chunks])

    def generate_related_questions(
        self, question: str, chunks: list[Result], max_questions: int | None = None
    ) -> list[str]:
        return generate_related_questions(
            question, [from_result(c) for c in chunks], max_questions or 5
        )

    async def find_related_questions(
        self,
        question: str,
        chunks: list[Result] | list,
        *,
        tenant_id: str = "global",
        collections: list[str] | None = None,
        max_questions: int | None = None,
    ) -> list[str]:
        used = [_coerce_related_chunk(item) for item in chunks or []]
        return await related_questions_knn(
            self._container.retrieve,
            question,
            used,
            tenant_id=tenant_id,
            collections=collections,
            max_questions=max_questions or 5,
        )

    async def simple_chat(
        self, question: str, history: list | None = None, temperature: float | None = None
    ):
        result = await self._container.answer.execute(
            question,
            history=history,
            use_rag=False,
            model=self.model,
            temperature=temperature,
        )
        return {
            "answer": result["answer"],
            "chunks": [],
            "retrieval": None,
            "related_questions": result["related_questions"],
        }

    async def answer(
        self,
        question: str,
        history: list | None = None,
        tenant_id: str = "global",
        collections: list[str] | None = None,
        model: str | None = None,
        use_reranking: bool | None = None,
        use_query_rewrite: bool | None = None,
        retrieval_strategy: str | None = None,
        temperature: float | None = None,
        on_token: Callable[[str], Awaitable[None] | None] | None = None,
    ):
        do_rerank = RAG_USE_RERANKER if use_reranking is None else bool(use_reranking)
        allow_rewrite = (
            RAG_USE_QUERY_REWRITE
            if use_query_rewrite is None
            else bool(use_query_rewrite)
        )
        if retrieval_strategy is None:
            from services.agentic_rag_service import chat_retrieval_strategy

            strategy = chat_retrieval_strategy(use_reranking=do_rerank)
        else:
            strategy = retrieval_strategy
        result = await self._container.answer.execute(
            question,
            tenant_id=tenant_id,
            collections=collections,
            history=history,
            model=model,
            use_reranking=do_rerank,
            use_query_rewrite=allow_rewrite,
            retrieval_strategy=strategy,
            temperature=temperature,
            on_token=on_token,
        )
        return self._public_answer(result)

    @staticmethod
    def _public_answer(result: dict[str, Any]) -> dict[str, Any]:
        chunks = result.get("chunks") or []
        if chunks and isinstance(chunks[0], RetrievedChunk):
            result["chunks"] = to_results(chunks)
        details = result.get("retrieval_details") or {}
        for key in (
            "chunks",
            "dense_original",
            "dense_rewritten",
            "bm25_original",
            "bm25_rewritten",
            "candidates",
        ):
            items = details.get(key)
            if items and isinstance(items[0], RetrievedChunk):
                details[key] = to_results(items)
        result["retrieval_details"] = details
        return result

    def invalidate_bm25_cache(self, tenant_id: str | None = None):
        self._container.lexical.invalidate(tenant_id)

    @staticmethod
    def invalidate_retrieval_cache(tenant_id: str | None = None) -> int:
        return invalidate_retrieval_cache(tenant_id)

    async def notify_index_updated(self, tenant_id: str) -> None:
        await self._container.ingest.execute(tenant_id)

    def calculate_mrr(self, keyword: str, retrieved_docs: list) -> float:
        return calculate_mrr(keyword, retrieved_docs)

    def calculate_dcg(self, relevances: list[int], k: int) -> float:
        return calculate_dcg(relevances, k)

    def calculate_ndcg(self, keyword: str, retrieved_docs: list, k: int = 10) -> float:
        return calculate_ndcg(keyword, retrieved_docs, k)

    async def evaluate_retrieval(
        self, test, tenant_id: str, collections: list[str] | None = None, k: int = 10
    ) -> RetrievalEval:
        return await self._container.evaluate_retrieval.execute(
            test, tenant_id, collections, k
        )

    async def _create_completion(
        self,
        model: str,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        temp = RAG_TEMPERATURE if temperature is None else float(temperature)
        tokens = RAG_MAX_TOKENS if max_tokens is None else int(max_tokens)
        return await asyncio.to_thread(
            self.client.chat.completions.create,
            model=model,
            messages=messages,
            temperature=temp,
            max_tokens=tokens,
            extra_body={
                "keep_alive": RAG_KEEP_ALIVE,
                "options": {"num_ctx": RAG_NUM_CTX, "num_predict": tokens},
            },
        )

    async def _stream_completion(
        self,
        model: str,
        messages: list[dict],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        on_token: Callable[[str], Awaitable[None] | None] | None = None,
    ) -> str:
        """Genera con stream=True y notifica cada delta (Ollama/OpenAI-compatible)."""
        temp = RAG_TEMPERATURE if temperature is None else float(temperature)
        tokens = RAG_MAX_TOKENS if max_tokens is None else int(max_tokens)
        queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _run() -> None:
            try:
                stream = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=tokens,
                    stream=True,
                    extra_body={
                        "keep_alive": RAG_KEEP_ALIVE,
                        "options": {"num_ctx": RAG_NUM_CTX, "num_predict": tokens},
                    },
                )
                for chunk in stream:
                    choice = chunk.choices[0] if chunk.choices else None
                    delta = (
                        (choice.delta.content or "")
                        if choice and choice.delta
                        else ""
                    )
                    if delta:
                        loop.call_soon_threadsafe(queue.put_nowait, ("token", delta))
                loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
            except Exception as exc:  # noqa: BLE001 — se re-lanza en el awaiter
                loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))

        worker = asyncio.create_task(asyncio.to_thread(_run))
        parts: list[str] = []
        while True:
            kind, payload = await queue.get()
            if kind == "token":
                parts.append(str(payload))
                if on_token is not None:
                    maybe = on_token(str(payload))
                    if maybe is not None and hasattr(maybe, "__await__"):
                        await maybe  # type: ignore[misc]
            elif kind == "done":
                break
            elif kind == "error":
                await worker
                raise payload
        await worker
        return "".join(parts)

    async def _create_parse_completion(
        self, model: str, messages: list[dict], response_format
    ):
        return await asyncio.to_thread(
            self.client.beta.chat.completions.parse,
            model=model,
            messages=messages,
            response_format=response_format,
        )

    async def evaluate_answer(
        self,
        question: str,
        generated_answer: str,
        retrieved_docs: list,
        reference_answer: str | None = None,
        out_of_knowledge: bool = False,
        keywords: list[str] | None = None,
    ):
        return await self._container.evaluate_answer.execute(
            question,
            generated_answer,
            retrieved_docs,
            reference_answer,
            out_of_knowledge,
            keywords,
        )

    def get_embeddings(self):
        return self.embedding_model

    async def knowledge_graph(self):
        stmt = (
            select(Chunk, Embedding, Document)
            .join(Embedding, Embedding.chunk_id == Chunk.id)
            .join(Document, Document.id == Chunk.document_id)
        )
        async with AsyncSessionLocal() as session:
            rows = (await session.execute(stmt)).all()
        graph = []
        for chunk, embedding, document in rows:
            graph.append(
                {
                    "document_id": str(document.id),
                    "source": document.filename,
                    "headline": chunk.headline,
                    "summary": chunk.summary,
                    "content": chunk.content,
                    "embedding_dimension": (
                        len(embedding.vector) if embedding.vector else 0
                    ),
                }
            )
        return graph
