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


def test_fingerprint_is_stable_but_split_sensitive():
    row = {
        "question": "¿Qué exige la BCAM 6?",
        "keywords": ["BCAM 6"],
        "reference_answer": "Cobertura del suelo.",
        "split": "dev",
    }
    assert dataset_fingerprint([row]) == dataset_fingerprint([{**row, "question": "  ¿QUÉ exige la BCAM 6? "}])
    assert dataset_fingerprint([row]) != dataset_fingerprint([{**row, "split": "holdout"}])
    assert normalize_text("Árida  ") == "arida"
