from __future__ import annotations

import os
import time
from collections.abc import Awaitable, Callable
from typing import Any

from rag.adapters.outbound.ollama import RAG_CHAT_MAX_TOKENS
from rag.application.prompts import OUT_OF_KNOWLEDGE_ANSWER, SYSTEM_PROMPT
from rag.application.retrieve import HybridRetrieve
from rag.domain.entities import RetrievalQuery, RetrievedChunk
from rag.domain.ports import LlmPort
from rag.domain.related import generate_related_questions

CHUNK_CHAR_LIMIT = int(os.getenv("RAG_CHUNK_CHAR_LIMIT", "1400"))
CHAT_CHUNK_CHAR_LIMIT = int(
    os.getenv("RAG_CHAT_CHUNK_CHAR_LIMIT", os.getenv("RAG_AGENT_CHUNK_CHARS", "700"))
)
RELATED_QUESTIONS = max(0, int(os.getenv("RAG_RELATED_QUESTIONS", "3")))
FAST_ABSTAIN = os.getenv("RAG_FAST_ABSTAIN", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
CHAT_FAST_GEN = os.getenv("RAG_CHAT_FAST_GEN", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

_FAST_STRATEGIES = {
    "dense",
    "hybrid_rrf",
    "hybrid_rrf_rerank",
}


def _is_chat_fast(strategy: str) -> bool:
    return CHAT_FAST_GEN and (strategy or "").strip().lower() in _FAST_STRATEGIES


def build_prompt(
    question: str,
    history: list,
    chunks: list[RetrievedChunk],
    *,
    compact: bool = False,
) -> list[dict[str, str]]:
    char_limit = CHAT_CHUNK_CHAR_LIMIT if compact else CHUNK_CHAR_LIMIT
    history_n = 2 if compact else 6
    parts = []
    for chunk in chunks:
        body = chunk.page_content or ""
        if len(body) > char_limit:
            body = body[:char_limit].rstrip() + "…"
        source = chunk.metadata.get("source", "fuente_desconocida")
        parts.append(f"Extrae de {source}:\n{body}")
    context = "\n\n".join(parts)
    trimmed = (history or [])[-history_n:]
    system = SYSTEM_PROMPT.format(context=context)
    if compact:
        system = (
            "Responde en español, breve y solo con el contexto. "
            "Si falta evidencia, dilo. Cita la fuente cuando puedas.\n\n"
            f"Contexto:\n{context or '(vacío)'}"
        )
    return (
        [{"role": "system", "content": system}]
        + trimmed
        + [{"role": "user", "content": question}]
    )


async def related_questions_knn(
    retrieve: HybridRetrieve,
    question: str,
    chunks: list[RetrievedChunk],
    *,
    tenant_id: str,
    collections: list[str] | None,
    max_questions: int,
    neighbors: list[RetrievedChunk] | None = None,
) -> list[str]:
    if max_questions <= 0:
        return []
    pool = list(neighbors or [])
    exclude_chunk_ids = [
        str(chunk.metadata.get("chunk_id"))
        for chunk in chunks
        if chunk.metadata.get("chunk_id")
    ]
    try:
        pool = await retrieve.chunks.retrieve_dense(
            question,
            tenant_id,
            collections,
            k=max(max_questions * 4, retrieve.retrieval_k),
            distance_metric="cosine",
            embedding_model=retrieve.embedding_model,
            exclude_chunk_ids=exclude_chunk_ids,
        )
    except TypeError:
        if not pool:
            pool = chunks
    return generate_related_questions(
        question, chunks, max_questions, neighbors=pool
    )


class AnswerQuestion:
    def __init__(self, retrieve: HybridRetrieve, llm: LlmPort, default_model: str):
        self.retrieve = retrieve
        self.llm = llm
        self.default_model = default_model

    async def execute(
        self,
        question: str,
        *,
        tenant_id: str = "global",
        collections: list[str] | None = None,
        history: list | None = None,
        model: str | None = None,
        use_reranking: bool = False,
        use_query_rewrite: bool = False,
        use_rag: bool = True,
        retrieval_strategy: str = "hybrid_expansion_rrf",
        temperature: float | None = None,
        on_token: Callable[[str], Awaitable[None] | None] | None = None,
    ) -> dict[str, Any]:
        history = history or []
        active_model = model or self.default_model
        compact = _is_chat_fast(retrieval_strategy)
        gen_tokens = RAG_CHAT_MAX_TOKENS if compact else None

        if not use_rag:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT.format(context="")},
                *(history[-2:] if compact else history),
                {"role": "user", "content": question},
            ]
            answer = await self.llm.complete(
                active_model,
                messages,
                temperature=temperature,
                max_tokens=gen_tokens,
            )
            return {
                "answer": answer,
                "chunks": [],
                "retrieval": None,
                "related_questions": await related_questions_knn(
                    self.retrieve,
                    question,
                    [],
                    tenant_id=tenant_id,
                    collections=collections,
                    max_questions=RELATED_QUESTIONS,
                ),
            }

        t_total = time.time()
        bundle = await self.retrieve.execute(
            RetrievalQuery(
                question=question,
                tenant_id=tenant_id,
                collections=collections,
                use_reranking=use_reranking,
                use_query_rewrite=use_query_rewrite,
                retrieval_strategy=retrieval_strategy,
            )
        )
        chunks = bundle.chunks
        related = await related_questions_knn(
            self.retrieve,
            question,
            chunks,
            tenant_id=tenant_id,
            collections=collections,
            max_questions=RELATED_QUESTIONS,
            neighbors=bundle.dense_original or bundle.dense_rewritten,
        )
        # Sin evidencia: respuesta plantilla al instante (sin inferencia LLM).
        if FAST_ABSTAIN and not chunks:
            bundle.retrieval.setdefault("timings_ms", {})["generation"] = 0.0
            bundle.retrieval["timings_ms"]["total_rag"] = (time.time() - t_total) * 1000
            bundle.retrieval["out_of_knowledge"] = True
            bundle.retrieval["generation_skipped"] = True
            return {
                "answer": OUT_OF_KNOWLEDGE_ANSWER,
                "chunks": chunks,
                "retrieval": bundle.retrieval,
                "retrieval_details": {
                    "chunks": chunks,
                    "rewritten_query": bundle.rewritten_query,
                    "dense_original": bundle.dense_original,
                    "dense_rewritten": bundle.dense_rewritten,
                    "bm25_original": bundle.bm25_original,
                    "bm25_rewritten": bundle.bm25_rewritten,
                    "candidates": bundle.candidates,
                    "retrieval": bundle.retrieval,
                    "related_questions": related,
                    "out_of_knowledge": True,
                    "generation_skipped": True,
                },
                "related_questions": related,
            }

        # Menos chunks al LLM en modo chat rápido.
        synth_chunks = chunks[: max(1, int(os.getenv("RAG_AGENT_CHUNK_N", "3")))] if compact else chunks
        messages = build_prompt(question, history, synth_chunks, compact=compact)
        t_gen = time.time()
        if on_token is not None and hasattr(self.llm, "stream"):
            answer = await self.llm.stream(
                active_model,
                messages,
                temperature=temperature,
                max_tokens=gen_tokens,
                on_token=on_token,
            )
        else:
            answer = await self.llm.complete(
                active_model,
                messages,
                temperature=temperature,
                max_tokens=gen_tokens,
            )
        generation_latency_ms = (time.time() - t_gen) * 1000
        bundle.retrieval.setdefault("timings_ms", {})["generation"] = (
            generation_latency_ms
        )
        bundle.retrieval["timings_ms"]["total_rag"] = (time.time() - t_total) * 1000
        if compact:
            bundle.retrieval["chat_fast_gen"] = True
            bundle.retrieval["chat_max_tokens"] = RAG_CHAT_MAX_TOKENS
        return {
            "answer": answer,
            "chunks": chunks,
            "retrieval": bundle.retrieval,
            "retrieval_details": {
                "chunks": chunks,
                "rewritten_query": bundle.rewritten_query,
                "dense_original": bundle.dense_original,
                "dense_rewritten": bundle.dense_rewritten,
                "bm25_original": bundle.bm25_original,
                "bm25_rewritten": bundle.bm25_rewritten,
                "candidates": bundle.candidates,
                "retrieval": bundle.retrieval,
                "related_questions": related,
            },
            "related_questions": related,
        }
