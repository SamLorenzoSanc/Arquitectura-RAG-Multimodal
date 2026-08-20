from __future__ import annotations

import os
import time
from typing import Any

from rag.application.prompts import SYSTEM_PROMPT
from rag.application.retrieve import HybridRetrieve
from rag.domain.entities import RetrievalQuery, RetrievedChunk
from rag.domain.ports import LlmPort
from rag.domain.related import generate_related_questions

CHUNK_CHAR_LIMIT = int(os.getenv("RAG_CHUNK_CHAR_LIMIT", "1400"))
RELATED_QUESTIONS = max(1, int(os.getenv("RAG_RELATED_QUESTIONS", "5")))


def build_prompt(
    question: str,
    history: list,
    chunks: list[RetrievedChunk],
) -> list[dict[str, str]]:
    parts = []
    for chunk in chunks:
        body = chunk.page_content or ""
        if len(body) > CHUNK_CHAR_LIMIT:
            body = body[:CHUNK_CHAR_LIMIT].rstrip() + "…"
        source = chunk.metadata.get("source", "fuente_desconocida")
        parts.append(f"Extrae de {source}:\n{body}")
    context = "\n\n".join(parts)
    trimmed = (history or [])[-6:]
    return (
        [{"role": "system", "content": SYSTEM_PROMPT.format(context=context)}]
        + trimmed
        + [{"role": "user", "content": question}]
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
    ) -> dict[str, Any]:
        history = history or []
        active_model = model or self.default_model
        if not use_rag:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT.format(context="")},
                *history,
                {"role": "user", "content": question},
            ]
            answer = await self.llm.complete(
                active_model, messages, temperature=temperature
            )
            return {
                "answer": answer,
                "chunks": [],
                "retrieval": None,
                "related_questions": generate_related_questions(
                    question, [], RELATED_QUESTIONS
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
        messages = build_prompt(question, history, chunks)
        t_gen = time.time()
        answer = await self.llm.complete(
            active_model, messages, temperature=temperature
        )
        generation_latency_ms = (time.time() - t_gen) * 1000
        related = generate_related_questions(question, chunks, RELATED_QUESTIONS)
        bundle.retrieval.setdefault("timings_ms", {})["generation"] = (
            generation_latency_ms
        )
        bundle.retrieval["timings_ms"]["total_rag"] = (time.time() - t_total) * 1000
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
