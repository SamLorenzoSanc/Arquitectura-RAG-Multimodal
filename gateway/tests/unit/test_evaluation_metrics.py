import pytest

from services.evaluation_metrics import (
    abstention_score,
    citation_accuracy,
    dataset_fingerprint,
    ndcg_at_k,
    normalize_text,
    numeric_match,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

pytestmark = pytest.mark.unit


def test_ir_metrics_have_standard_denominators():
    relevant = {"a", "c"}
    retrieved = ["x", "a", "c"]
    assert precision_at_k(relevant, retrieved, 2) == 0.5
    assert recall_at_k(relevant, retrieved, 2) == 0.5
    assert reciprocal_rank(relevant, retrieved) == 0.5
    assert ndcg_at_k(relevant, retrieved, 3) == pytest.approx(0.6934264)


def test_numeric_matching_handles_spanish_formats_and_tolerance():
    reference = "La ayuda es 1.200 € por hectárea y el límite 4.500 m³."
    assert numeric_match(reference, "Ayuda: 1200 EUR; límite: 4 500 m3.") == 1.0
    assert numeric_match("100 €", "101 €", tolerance=0.01) == 1.0
    assert numeric_match("100 €", "103 €", tolerance=0.01) == 0.0


def test_citations_and_abstention_are_deterministic():
    assert citation_accuracy("Véase [manual.pdf:p. 12].", ["manual.pdf"]) == 1.0
    assert citation_accuracy("La ayuda es 1.200 € por hectárea.", ["posei.pdf"]) == 1.0
    assert citation_accuracy("Según [inventado.pdf] el POSEI paga 10 €.", ["posei.pdf"]) == 0.0
    assert abstention_score("El contexto no contiene esa información.", True) == 1.0
    assert abstention_score("La dosis es 3 ml.", True) == 0.0


def test_keyword_ir_metrics_are_shared_by_context_and_answer():
    from services.evaluation_metrics import keyword_ir_metrics, split_answer_units

    keywords = ["filtro", "gotero"]
    context = [
        "Revisa el filtro de malla.",
        "Sustituye goteros ciegos.",
        "El viento alisio parte hojas.",
    ]
    context_metrics = keyword_ir_metrics(keywords, context, k=3)
    assert context_metrics["keywords_found"] == 2
    assert context_metrics["mrr"] == pytest.approx(0.75)
    answer = "Limpia el filtro y cambia el gotero ciego."
    answer_metrics = keyword_ir_metrics(keywords, split_answer_units(answer), k=10)
    assert answer_metrics["keyword_coverage"] == 100.0
    assert answer_metrics["mrr"] == 1.0
    row = {
        "question": "¿Qué exige la BCAM 6?",
        "keywords": ["BCAM 6"],
        "reference_answer": "Cobertura del suelo.",
        "split": "dev",
    }
    assert dataset_fingerprint([row]) == dataset_fingerprint([{**row, "question": "  ¿QUÉ exige la BCAM 6? "}])
    assert dataset_fingerprint([row]) != dataset_fingerprint([{**row, "split": "holdout"}])
    assert normalize_text("Árida  ") == "arida"


def test_retrieval_eval_exposes_same_ir_and_five_scale_notes():
    from rag.application.evaluate import ir_from_texts

    result = ir_from_texts(
        ["filtro", "gotero"],
        ["Revisa el filtro de malla.", "Sustituye goteros ciegos."],
        k=2,
    )
    assert result.keyword_coverage == 100.0
    assert result.completeness == pytest.approx(5.0)
    assert result.relevance == pytest.approx(round(1.0 + 4.0 * result.ndcg, 2))
