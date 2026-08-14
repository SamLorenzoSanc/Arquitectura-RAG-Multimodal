from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, Field

from rag.application.retrieve import HybridRetrieve
from rag.domain.entities import RetrievalQuery, RetrievedChunk
from rag.domain.ports import LlmPort
from schemas.evaluation import AnswerEvaluation
from services.evaluation_metrics import (
    abstention_score,
    citation_accuracy,
    normalize_text,
    numeric_match,
)


class RetrievalEval(BaseModel):
    mrr: float = Field(description="Mean Reciprocal Rank")
    ndcg: float = Field(description="Normalized Discounted Cumulative Gain")
    keywords_found: int = Field(description="Número de keywords encontradas")
    total_keywords: int = Field(description="Número total de keywords")
    keyword_coverage: float = Field(description="Cobertura porcentual de keywords")
    accuracy: float = Field(description="Acierto globales de la búsqueda")


def _doc_text(doc: Any) -> str:
    return normalize_text(
        getattr(doc, "page_content", None)
        or (doc.get("page_content") if isinstance(doc, dict) else "")
        or str(doc)
    )


def calculate_mrr(keyword: str, retrieved_docs: list) -> float:
    needle = normalize_text(keyword)
    if not needle:
        return 0.0
    for rank, doc in enumerate(retrieved_docs, start=1):
        if needle in _doc_text(doc):
            return 1.0 / rank
    return 0.0


def calculate_dcg(relevances: list[int], k: int) -> float:
    dcg = 0.0
    for i in range(min(k, len(relevances))):
        dcg += relevances[i] / math.log2(i + 2)
    return dcg


def calculate_ndcg(keyword: str, retrieved_docs: list, k: int = 10) -> float:
    needle = normalize_text(keyword)
    relevances = [
        1 if needle and needle in _doc_text(doc) else 0 for doc in retrieved_docs[:k]
    ]
    dcg = calculate_dcg(relevances, k)
    idcg = calculate_dcg(sorted(relevances, reverse=True), k)
    return dcg / idcg if idcg > 0 else 0.0


class EvaluateRetrieval:
    def __init__(self, retrieve: HybridRetrieve):
        self.retrieve = retrieve

    async def execute(
        self, test: Any, tenant_id: str, collections: list[str] | None = None, k: int = 10
    ) -> RetrievalEval:
        bundle = await self.retrieve.execute(
            RetrievalQuery(
                question=test.question,
                tenant_id=tenant_id,
                collections=collections,
                evaluation_mode=True,
            )
        )
        retrieved_docs = bundle.chunks
        top_k = retrieved_docs[:k]
        mrr_scores = [calculate_mrr(kw, retrieved_docs) for kw in test.keywords]
        ndcg_scores = [calculate_ndcg(kw, retrieved_docs, k) for kw in test.keywords]
        avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0
        avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0
        keywords_found = sum(1 for score in mrr_scores if score > 0)
        total_keywords = len(test.keywords)
        coverage = (keywords_found / total_keywords * 100) if total_keywords else 0.0
        relevant = 0
        for doc in top_k:
            text = getattr(doc, "page_content", str(doc))
            if any(keyword.lower() in text.lower() for keyword in test.keywords):
                relevant += 1
        accuracy = (relevant / len(top_k) * 100) if top_k else 0.0
        return RetrievalEval(
            mrr=avg_mrr,
            ndcg=avg_ndcg,
            keywords_found=keywords_found,
            total_keywords=total_keywords,
            keyword_coverage=coverage,
            accuracy=accuracy,
        )


class EvaluateAnswer:
    def __init__(self, llm: LlmPort, model: str):
        self.llm = llm
        self.model = model

    async def execute(
        self,
        question: str,
        generated_answer: str,
        retrieved_docs: list,
        reference_answer: str | None = None,
        out_of_knowledge: bool = False,
    ) -> tuple[AnswerEvaluation, str, list]:
        context = "\n\n".join(
            getattr(doc, "page_content", str(doc)) for doc in retrieved_docs
        )
        sources = [
            str(getattr(doc, "metadata", {}).get("source", ""))
            for doc in retrieved_docs
        ]
        prompt = f"""
        Pregunta: {question}
        Respuesta de referencia: {reference_answer or "No disponible"}
        Respuesta Generada: {generated_answer}
        Contexto recuperado: {context or "Sin contexto"}
        Fuera de conocimiento: {out_of_knowledge}
        Puntúa accuracy, precision, completeness, relevance, faithfulness y groundedness de 1 a 5.
        precision mide si la respuesta va al grano, sin relleno ni invención.
        citation_accuracy, numeric_match y abstention deben estar entre 0 y 1.
        La referencia mide corrección; el contexto mide fidelidad. No premies afirmaciones
        correctas que no estén respaldadas por el contexto cuando se evalúe groundedness.
        """
        eval_result = await self.llm.parse(
            self.model,
            [
                {
                    "role": "system",
                    "content": "Eres un evaluador experto. Responde solo en JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            AnswerEvaluation,
        )
        if eval_result is None:
            raise RuntimeError("El juez no devolvió una evaluación estructurada")
        eval_result.numeric_match = numeric_match(reference_answer, generated_answer)
        eval_result.citation_accuracy = citation_accuracy(generated_answer, sources)
        eval_result.abstention = abstention_score(generated_answer, out_of_knowledge)
        return eval_result, generated_answer, retrieved_docs
