import sys
import os
import math
import json
import re
import urllib.request
from pydantic import BaseModel, Field
from dotenv import load_dotenv

try:
    from .test import TestQuestion, load_tests
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from evaluation.test import TestQuestion, load_tests

from advanced_implementation.answer import answer_question, fetch_context


load_dotenv(override=True)

MODEL = os.getenv("RAG_GENERATION_MODEL", "llama3.2")
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", os.getenv("OLLAMA_URL", "http://localhost:11434"))


def _normalize(value: str) -> str:
    return " ".join((value or "").casefold().split())


def _doc_text(doc) -> str:
    return getattr(doc, "page_content", None) or str(doc)


def _answer_units(answer: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", (answer or "").strip())
    return [part.strip() for part in parts if part.strip()] or ([answer] if answer else [])


class SharedIREval(BaseModel):
    """Métricas de recuperación compartidas por contexto y por respuesta."""

    mrr: float = Field(default=0.0, description="Rango recíproco medio de las palabras clave")
    ndcg: float = Field(default=0.0, description="nDCG binario de las palabras clave")
    keywords_found: int = Field(default=0, description="Palabras clave encontradas")
    total_keywords: int = Field(default=0, description="Palabras clave esperadas")
    keyword_coverage: float = Field(
        default=0.0, description="Porcentaje de palabras clave encontradas"
    )


class RetrievalEval(SharedIREval):
    """Contexto recuperado: mismas IR que la respuesta, más notas 1-5 comparables."""

    accuracy: float = Field(description="Precisión@k (0-100) de fragmentos con palabras clave")
    completeness: float = Field(description="Cobertura de palabras clave, en escala 1-5")
    relevance: float = Field(description="Calidad del ranking (nDCG), en escala 1-5")


class JudgeScores(BaseModel):
    feedback: str
    accuracy: float = Field(ge=1, le=5)
    completeness: float = Field(ge=1, le=5)
    relevance: float = Field(ge=1, le=5)
    faithfulness: float = Field(ge=1, le=5, default=3)


class AnswerEval(SharedIREval):
    """Las mismas métricas IR que el retrieval, más el juez LLM 1-5."""

    feedback: str = Field(
        description="Comentarios concisos comparando respuesta, referencia y contexto recuperado"
    )
    accuracy: float = Field(
        description="Corrección fáctica frente a la referencia. 1 incorrecta, 5 perfecta"
    )
    completeness: float = Field(description="¿Cubre toda la información de la referencia? 1-5")
    relevance: float = Field(description="¿Responde a la pregunta sin relleno? 1-5")
    faithfulness: float = Field(default=3, description="¿Está anclada en el contexto recuperado? 1-5")


def _to_five(unit: float) -> float:
    return round(1.0 + 4.0 * max(0.0, min(1.0, unit)), 2)


def calculate_mrr(keyword: str, retrieved_docs: list) -> float:
    needle = _normalize(keyword)
    if not needle:
        return 0.0
    for rank, doc in enumerate(retrieved_docs, start=1):
        if needle in _normalize(_doc_text(doc)):
            return 1.0 / rank
    return 0.0


def calculate_dcg(relevances: list[int], k: int) -> float:
    dcg = 0.0
    for i in range(min(k, len(relevances))):
        dcg += relevances[i] / math.log2(i + 2)
    return dcg


def calculate_ndcg(keyword: str, retrieved_docs: list, k: int = 10) -> float:
    needle = _normalize(keyword)
    relevances = [
        1 if needle and needle in _normalize(_doc_text(doc)) else 0
        for doc in retrieved_docs[:k]
    ]
    dcg = calculate_dcg(relevances, k)
    idcg = calculate_dcg(sorted(relevances, reverse=True), k)
    return dcg / idcg if idcg > 0 else 0.0


def ir_metrics(keywords: list[str], docs: list, k: int = 10) -> dict:
    needles = [item for item in keywords if _normalize(item)]
    ranked = docs[:k]
    if not needles:
        return {
            "mrr": 0.0,
            "ndcg": 0.0,
            "keywords_found": 0,
            "total_keywords": 0,
            "keyword_coverage": 0.0,
            "accuracy": 0.0,
        }
    mrr_scores = [calculate_mrr(item, ranked) for item in needles]
    ndcg_scores = [calculate_ndcg(item, ranked, k) for item in needles]
    found = sum(1 for score in mrr_scores if score > 0)
    relevant = 0
    for doc in ranked:
        blob = _normalize(_doc_text(doc))
        if any(_normalize(item) in blob for item in needles):
            relevant += 1
    return {
        "mrr": sum(mrr_scores) / len(mrr_scores),
        "ndcg": sum(ndcg_scores) / len(ndcg_scores),
        "keywords_found": found,
        "total_keywords": len(needles),
        "keyword_coverage": found / len(needles) * 100.0,
        "accuracy": (relevant / len(ranked) * 100.0) if ranked else 0.0,
    }


class _TextDoc:
    def __init__(self, page_content: str):
        self.page_content = page_content


def evaluate_retrieval(test: TestQuestion, k: int = 10, retrieved_docs: list | None = None) -> RetrievalEval:
    docs = retrieved_docs if retrieved_docs is not None else fetch_context(test.question)
    metrics = ir_metrics(test.keywords, docs, k)
    coverage_unit = metrics["keyword_coverage"] / 100.0
    return RetrievalEval(
        **metrics,
        completeness=_to_five(coverage_unit),
        relevance=_to_five(metrics["ndcg"]),
    )


def evaluate_answer(test: TestQuestion) -> tuple[AnswerEval, str, list, RetrievalEval]:
    """Una sola recuperación: evalúa contexto y respuesta con las mismas métricas IR."""
    generated_answer, docs = answer_question(test.question)
    retrieval = evaluate_retrieval(test, retrieved_docs=docs)
    context = "\n\n".join(_doc_text(doc) for doc in docs)
    ir = ir_metrics(test.keywords, [_TextDoc(unit) for unit in _answer_units(generated_answer)])

    judge_messages = [
        {
            "role": "system",
            "content": (
                "Eres un evaluador experto. Valora la respuesta con la misma vara que el retrieval: "
                "cobertura de palabras clave, ranking de lo importante y fidelidad al contexto. "
                "Solo otorga 5/5 a respuestas perfectas y ancladas en el contexto."
            ),
        },
        {
            "role": "user",
            "content": f"""Pregunta:
{test.question}

Respuesta generada:
{generated_answer}

Respuesta de referencia:
{test.reference_answer}

Contexto recuperado:
{context or "Sin contexto"}

Palabras clave esperadas: {", ".join(test.keywords)}

Evalúa en tres aspectos (1 muy deficiente, 5 ideal):
1. Precisión (quality_accuracy): corrección fáctica frente a la referencia. Si es incorrecta, 1.
2. Exhaustividad (completeness): ¿incluye TODA la información de la referencia?
3. Pertinencia (relevance): ¿responde a la pregunta sin relleno?
4. Fidelidad (faithfulness): ¿está anclada en el contexto recuperado?

No inventes mrr ni ndcg. Devuelve feedback y las notas 1-5.""",
        },
    ]

    payload = {
        "model": MODEL,
        "messages": judge_messages,
        "format": JudgeScores.model_json_schema(),
        "stream": False,
    }
    req = urllib.request.Request(
        f"{OLLAMA_API_BASE}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        json_content = res_data["message"]["content"]

    judged = JudgeScores.model_validate_json(json_content)
    answer_eval = AnswerEval(
        feedback=judged.feedback,
        accuracy=judged.accuracy,
        completeness=judged.completeness,
        relevance=judged.relevance,
        faithfulness=judged.faithfulness,
        mrr=ir["mrr"],
        ndcg=ir["ndcg"],
        keywords_found=ir["keywords_found"],
        total_keywords=ir["total_keywords"],
        keyword_coverage=ir["keyword_coverage"],
    )
    return answer_eval, generated_answer, docs, retrieval


def evaluate_all_retrieval():
    tests = load_tests()
    total_tests = len(tests)
    for index, test in enumerate(tests):
        result = evaluate_retrieval(test)
        progress = (index + 1) / total_tests
        yield test, result, progress


def evaluate_all_answers():
    tests = load_tests()
    total_tests = len(tests)
    for index, test in enumerate(tests):
        result = evaluate_answer(test)[0]
        progress = (index + 1) / total_tests
        yield test, result, progress


def run_cli_evaluation(test_number: int):
    tests = load_tests()
    if test_number < 0 or test_number >= len(tests):
        print(f"Error: test_row_number must be between 0 and {len(tests) - 1}")
        sys.exit(1)

    test = tests[test_number]
    print(f"\n{'=' * 80}")
    print(f"Test #{test_number}")
    print(f"{'=' * 80}")
    print(f"Question: {test.question}")
    print(f"Keywords: {test.keywords}")
    print(f"Category: {test.category}")
    print(f"Reference Answer: {test.reference_answer}")

    answer_result, generated_answer, retrieved_docs, retrieval_result = evaluate_answer(test)

    print(f"\n{'=' * 80}")
    print("Retrieval y respuesta (mismas métricas IR)")
    print(f"{'=' * 80}")
    print("Contexto:")
    print(f"  MRR: {retrieval_result.mrr:.4f}  nDCG: {retrieval_result.ndcg:.4f}")
    print(
        f"  Cobertura: {retrieval_result.keywords_found}/{retrieval_result.total_keywords} "
        f"({retrieval_result.keyword_coverage:.1f}%)  Precisión@k: {retrieval_result.accuracy:.1f}%"
    )
    print(
        f"  Notas 1-5  exhaustividad {retrieval_result.completeness:.2f}  "
        f"pertinencia {retrieval_result.relevance:.2f}"
    )
    print("Respuesta:")
    print(f"  MRR: {answer_result.mrr:.4f}  nDCG: {answer_result.ndcg:.4f}")
    print(
        f"  Cobertura: {answer_result.keywords_found}/{answer_result.total_keywords} "
        f"({answer_result.keyword_coverage:.1f}%)"
    )
    print(f"\nGenerated Answer:\n{generated_answer}")
    print(f"\nFeedback:\n{answer_result.feedback}")
    print("\nScores 1-5:")
    print(f"  Accuracy: {answer_result.accuracy:.2f}/5")
    print(f"  Completeness: {answer_result.completeness:.2f}/5")
    print(f"  Relevance: {answer_result.relevance:.2f}/5")
    print(f"  Faithfulness: {answer_result.faithfulness:.2f}/5")
    print(f"\n{'=' * 80}\n")


def main():
    if len(sys.argv) != 2:
        print("Usage: python eval.py <test_row_number>")
        sys.exit(1)
    try:
        test_number = int(sys.argv[1])
    except ValueError:
        print("Error: test_row_number must be an integer")
        sys.exit(1)
    run_cli_evaluation(test_number)


if __name__ == "__main__":
    main()
