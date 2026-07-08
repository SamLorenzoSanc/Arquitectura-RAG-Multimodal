import sys
import os
import math
from pydantic import BaseModel, Field
from litellm import completion
from dotenv import load_dotenv

from .test import TestQuestion, load_tests
from advanced_implementation.answer import answer_question, fetch_context


load_dotenv(override=True)

MODEL = "ollama/llama3"
db_name = "vector_db"


class RetrievalEval(BaseModel):
    """Evaluation metrics for retrieval performance."""

    mrr: float = Field(description="Rango recíproco medio: media de todas las palabras clave")
    ndcg: float = Field(description="Ganancia acumulada descontada normalizada (relevancia binaria)")
    keywords_found: int = Field(description="Número total de palabras clave que hay que buscar")
    total_keywords: int = Field(description="Número total de palabras clave que hay que buscar")
    keyword_coverage: float = Field(description="Porcentaje de palabras clave encontradas")


class AnswerEval(BaseModel):
    """LLM-as-a-judge evaluation of answer quality."""

    feedback: str = Field(
        description="Comentarios concisos sobre la calidad de la respuesta, comparándola con la respuesta de referencia y evaluándola en función del contexto obtenido"
    )
    accuracy: float = Field(
        description="¿En qué medida es correcta la respuesta desde el punto de vista fáctico en comparación con la respuesta de referencia? De 1 (incorrecta; cualquier respuesta incorrecta debe puntuar con un 1) a 5 (ideal: totalmente correcta). Una respuesta aceptable obtendría una puntuación de 3."
    )
    completeness: float = Field(
        description="¿En qué medida aborda la respuesta todos los aspectos de la pregunta? De 1 (muy deficiente: falta información clave) a 5 (ideal: se proporciona toda la información de la respuesta de referencia de forma completa). Responde 5 solo si se incluye TODA la información de la respuesta de referencia."
    )
    relevance: float = Field(
        description="¿En qué medida es relevante la respuesta a la pregunta concreta que se ha formulado? De 1 (muy poco relevante —fuera de tema—) a 5 (ideal —responde directamente a la pregunta y no aporta información adicional—). Responde con un 5 solo si la respuesta es totalmente relevante para la pregunta y no aporta información adicional."
    )


def calculate_mrr(keyword: str, retrieved_docs: list) -> float:
    """Calculate reciprocal rank for a single keyword (case-insensitive)."""
    keyword_lower = keyword.lower()
    for rank, doc in enumerate(retrieved_docs, start=1):
        if keyword_lower in doc.page_content.lower():
            return 1.0 / rank
    return 0.0


def calculate_dcg(relevances: list[int], k: int) -> float:
    """Calculate Discounted Cumulative Gain."""
    dcg = 0.0
    for i in range(min(k, len(relevances))):
        dcg += relevances[i] / math.log2(i + 2)  # i+2 because rank starts at 1
    return dcg


def calculate_ndcg(keyword: str, retrieved_docs: list, k: int = 10) -> float:
    """Calculate nDCG for a single keyword (binary relevance, case-insensitive)."""
    keyword_lower = keyword.lower()

    # Binary relevance: 1 if keyword found, 0 otherwise
    relevances = [
        1 if keyword_lower in doc.page_content.lower() else 0 for doc in retrieved_docs[:k]
    ]

    # DCG
    dcg = calculate_dcg(relevances, k)

    # Ideal DCG (best case: keyword in first position)
    ideal_relevances = sorted(relevances, reverse=True)
    idcg = calculate_dcg(ideal_relevances, k)

    return dcg / idcg if idcg > 0 else 0.0


def evaluate_retrieval(test: TestQuestion, k: int = 10) -> RetrievalEval:
    """
    Evaluate retrieval performance for a test question.

    Args:
        test: TestQuestion object containing question and keywords
        k: Number of top documents to retrieve (default 10)

    Returns:
        RetrievalEval object with MRR, nDCG, and keyword coverage metrics
    """
    # Retrieve documents using shared answer module
    retrieved_docs = fetch_context(test.question)

    # Calculate MRR (average across all keywords)
    mrr_scores = [calculate_mrr(keyword, retrieved_docs) for keyword in test.keywords]
    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0

    # Calculate nDCG (average across all keywords)
    ndcg_scores = [calculate_ndcg(keyword, retrieved_docs, k) for keyword in test.keywords]
    avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0

    # Calculate keyword coverage
    keywords_found = sum(1 for score in mrr_scores if score > 0)
    total_keywords = len(test.keywords)
    keyword_coverage = (keywords_found / total_keywords * 100) if total_keywords > 0 else 0.0

    return RetrievalEval(
        mrr=avg_mrr,
        ndcg=avg_ndcg,
        keywords_found=keywords_found,
        total_keywords=total_keywords,
        keyword_coverage=keyword_coverage,
    )


def evaluate_answer(test: TestQuestion) -> tuple[AnswerEval, str, list]:
    """
    Evaluate answer quality using LLM-as-a-judge (async).

    Args:
        test: TestQuestion object containing question and reference answer

    Returns:
        Tuple of (AnswerEval object, generated_answer string, retrieved_docs list)
    """
    # Get RAG response using shared answer module
    generated_answer, retrieved_docs = answer_question(test.question)

    # LLM judge prompt
    judge_messages = [
        {
            "role": "system",
            "content": "Eres un evaluador experto encargado de valorar la calidad de las respuestas. Evalúa la respuesta generada comparándola con la respuesta de referencia. Solo otorga una puntuación de 5/5 a las respuestas perfectas.",
        },
        {
            "role": "user",
            "content": f"""Pregunta:
            {test.question}

            Respuesta generada:
            {generated_answer}

            Respuesta de referencia:
            {test.reference_answer}

            Por favor, evalúa la respuesta generada en tres aspectos:
            1. Precisión: ¿En qué medida es correcta desde el punto de vista fáctico en comparación con la respuesta de referencia? Solo otorga una puntuación de 5/5 a las respuestas perfectas.
            2. Exhaustividad: ¿En qué medida aborda de forma exhaustiva todos los aspectos de la pregunta, cubriendo toda la información de la respuesta de referencia?
            3. Pertinencia: ¿En qué medida responde directamente a la pregunta específica formulada, sin aportar información adicional?

            Proporcione comentarios detallados y puntuaciones del 1 (muy deficiente) al 5 (ideal) para cada aspecto. Si la respuesta es incorrecta, la puntuación de precisión debe ser 1.«»"Por favor, evalúe la respuesta generada en tres aspectos:
            1. Precisión: ¿En qué medida es correcta desde el punto de vista fáctico en comparación con la respuesta de referencia? Solo otorgue una puntuación de 5/5 a las respuestas perfectas.
            2. Exhaustividad: ¿Hasta qué punto aborda de forma exhaustiva todos los aspectos de la pregunta, cubriendo toda la información de la respuesta de referencia?
            3. Pertinencia: ¿En qué medida responde directamente a la pregunta específica formulada, sin aportar información adicional?""",
        },
    ]

    # Call LLM judge with structured outputs (async)
    judge_response = completion(
        model=MODEL, 
        messages=judge_messages,
        custom_llm_provider="ollama",
        response_format={ "type": "json_object", "schema": AnswerEval.model_json_schema()},
        api_base="http://localhost:11434"
    )

    print(judge_response)

    judge_response = completion(model=MODEL, messages=judge_messages, response_format=AnswerEval)

    answer_eval = AnswerEval.model_validate_json(judge_response.choices[0].message.content)

    return answer_eval, generated_answer, retrieved_docs


def evaluate_all_retrieval():
    """Evaluate all retrieval tests."""
    tests = load_tests()
    total_tests = len(tests)
    for index, test in enumerate(tests):
        result = evaluate_retrieval(test)
        progress = (index + 1) / total_tests
        yield test, result, progress


def evaluate_all_answers():
    """Evaluate all answers to tests using batched async execution."""
    tests = load_tests()
    total_tests = len(tests)
    for index, test in enumerate(tests):
        result = evaluate_answer(test)[0]
        progress = (index + 1) / total_tests
        yield test, result, progress


def run_cli_evaluation(test_number: int):
    """Run evaluation for a specific test (async helper for CLI)."""
    # Load tests
    tests = load_tests("tests.jsonl")

    if test_number < 0 or test_number >= len(tests):
        print(f"Error: test_row_number must be between 0 and {len(tests) - 1}")
        sys.exit(1)

    # Get the test
    test = tests[test_number]

    # Print test info
    print(f"\n{'=' * 80}")
    print(f"Test #{test_number}")
    print(f"{'=' * 80}")
    print(f"Question: {test.question}")
    print(f"Keywords: {test.keywords}")
    print(f"Category: {test.category}")
    print(f"Reference Answer: {test.reference_answer}")

    # Retrieval Evaluation
    print(f"\n{'=' * 80}")
    print("Retrieval Evaluation")
    print(f"{'=' * 80}")

    retrieval_result = evaluate_retrieval(test)

    print(f"MRR: {retrieval_result.mrr:.4f}")
    print(f"nDCG: {retrieval_result.ndcg:.4f}")
    print(f"Keywords Found: {retrieval_result.keywords_found}/{retrieval_result.total_keywords}")
    print(f"Keyword Coverage: {retrieval_result.keyword_coverage:.1f}%")

    # Answer Evaluation
    print(f"\n{'=' * 80}")
    print("Answer Evaluation")
    print(f"{'=' * 80}")

    answer_result, generated_answer, retrieved_docs = evaluate_answer(test)

    print(f"\nGenerated Answer:\n{generated_answer}")
    print(f"\nFeedback:\n{answer_result.feedback}")
    print("\nScores:")
    print(f"  Accuracy: {answer_result.accuracy:.2f}/5")
    print(f"  Completeness: {answer_result.completeness:.2f}/5")
    print(f"  Relevance: {answer_result.relevance:.2f}/5")
    print(f"\n{'=' * 80}\n")


def main():
    """CLI to evaluate a specific test by row number."""
    if len(sys.argv) != 2:
        print("Usage: uv run eval.py <test_row_number>")
        sys.exit(1)

    try:
        test_number = int(sys.argv[1])
    except ValueError:
        print("Error: test_row_number must be an integer")
        sys.exit(1)

    run_cli_evaluation(test_number)


if __name__ == "__main__":
    main()
