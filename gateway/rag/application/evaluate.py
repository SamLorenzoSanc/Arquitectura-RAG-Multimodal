from __future__ import annotations

import math
from typing import Any, Sequence

from pydantic import BaseModel, Field

from rag.application.retrieve import HybridRetrieve
from rag.domain.entities import RetrievalQuery
from rag.domain.ports import LlmPort
from schemas.evaluation import AnswerEvaluation
from services.evaluation_metrics import (
    abstention_score,
    citation_accuracy,
    keyword_hit_rank,
    keyword_ir_metrics,
    normalize_text,
    numeric_match,
    split_answer_units,
)


def _to_five(unit: float) -> float:
    return round(1.0 + 4.0 * max(0.0, min(1.0, float(unit))), 2)


class RetrievalEval(BaseModel):
    mrr: float = Field(description="Mean Reciprocal Rank")
    ndcg: float = Field(description="Normalized Discounted Cumulative Gain")
    keywords_found: int = Field(description="Número de keywords encontradas")
    total_keywords: int = Field(description="Número total de keywords")
    keyword_coverage: float = Field(description="Cobertura porcentual de keywords")
    accuracy: float = Field(description="Acierto globales de la búsqueda")
    completeness: float = Field(
        default=1.0,
        description="Cobertura de palabras clave, en escala 1-5",
    )
    relevance: float = Field(
        default=1.0,
        description="Calidad del ranking (nDCG), en escala 1-5",
    )


def _doc_text(doc: Any) -> str:
    return (
        getattr(doc, "page_content", None)
        or (doc.get("page_content") if isinstance(doc, dict) else "")
        or str(doc)
    )


def calculate_mrr(keyword: str, retrieved_docs: list) -> float:
    return keyword_hit_rank(keyword, [_doc_text(doc) for doc in retrieved_docs])


def calculate_dcg(relevances: list[int], k: int) -> float:
    dcg = 0.0
    for i in range(min(k, len(relevances))):
        dcg += relevances[i] / math.log2(i + 2)
    return dcg


def calculate_ndcg(keyword: str, retrieved_docs: list, k: int = 10) -> float:
    from services.evaluation_metrics import keyword_ndcg

    return keyword_ndcg(keyword, [_doc_text(doc) for doc in retrieved_docs], k)


def retrieval_eval_from_values(
    *,
    mrr: float,
    ndcg: float,
    keywords_found: int,
    total_keywords: int,
    keyword_coverage: float,
    accuracy: float,
) -> RetrievalEval:
    return RetrievalEval(
        mrr=float(mrr),
        ndcg=float(ndcg),
        keywords_found=int(keywords_found),
        total_keywords=int(total_keywords),
        keyword_coverage=float(keyword_coverage),
        accuracy=float(accuracy),
        completeness=_to_five(float(keyword_coverage) / 100.0),
        relevance=_to_five(float(ndcg)),
    )


def ir_from_texts(keywords: Sequence[str], texts: Sequence[str], k: int = 10) -> RetrievalEval:
    metrics = keyword_ir_metrics(keywords, texts, k)
    return retrieval_eval_from_values(
        mrr=float(metrics["mrr"]),
        ndcg=float(metrics["ndcg"]),
        keywords_found=int(metrics["keywords_found"]),
        total_keywords=int(metrics["total_keywords"]),
        keyword_coverage=float(metrics["keyword_coverage"]),
        accuracy=float(metrics["accuracy"]),
    )


def apply_ir_to_answer(
    evaluation: AnswerEvaluation,
    keywords: Sequence[str],
    generated_answer: str,
    k: int = 10,
) -> AnswerEvaluation:
    metrics = keyword_ir_metrics(keywords, split_answer_units(generated_answer), k)
    evaluation.mrr = float(metrics["mrr"])
    evaluation.ndcg = float(metrics["ndcg"])
    evaluation.keywords_found = int(metrics["keywords_found"])
    evaluation.total_keywords = int(metrics["total_keywords"])
    evaluation.keyword_coverage = float(metrics["keyword_coverage"])
    return evaluation


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
        return ir_from_texts(
            test.keywords or [],
            [_doc_text(doc) for doc in bundle.chunks],
            k,
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
        keywords: Sequence[str] | None = None,
    ) -> tuple[AnswerEvaluation, str, list]:
        context = "\n\n".join(_doc_text(doc) for doc in retrieved_docs)
        sources = [
            str((getattr(doc, "metadata", None) or {}).get("source", ""))
            if not isinstance(doc, dict)
            else str((doc.get("metadata") or {}).get("source", ""))
            for doc in retrieved_docs
        ]
        prompt = f"""
        Pregunta: {question}
        Respuesta de referencia: {reference_answer or "No disponible"}
        Respuesta Generada: {generated_answer}
        Contexto recuperado: {context or "Sin contexto"}
        Fuera de conocimiento: {out_of_knowledge}
        Palabras clave esperadas: {", ".join(keywords or []) or "ninguna"}
        Puntúa accuracy, precision, completeness, relevance, faithfulness y groundedness de 1 a 5.
        Usa la misma vara que en recuperación: coverage (¿están las palabras clave?),
        ranking (¿lo importante va primero?) y fidelidad al contexto.
        precision mide si la respuesta va al grano, sin relleno ni invención.
        citation_accuracy, numeric_match y abstention deben estar entre 0 y 1.
        No rellenes mrr, ndcg ni keyword_coverage: se calculan aparte.
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
        apply_ir_to_answer(eval_result, keywords or [], generated_answer)
        return eval_result, generated_answer, retrieved_docs
