"""Tests del adaptador RAGAS (sin ejecutar el stack completo)."""

from __future__ import annotations

import pytest

from evaluation.ragas import (
    RagasSample,
    aggregate_ragas_scores,
    build_ragas_records,
    run_ragas_evaluation,
)

pytestmark = pytest.mark.unit


def test_build_ragas_records():
    records = build_ragas_records(
        [
            RagasSample(
                user_input="¿Qué es SIGPAC?",
                retrieved_contexts=["SIGPAC identifica parcelas."],
                response="SIGPAC identifica parcelas agrícolas.",
                reference="Sistema de identificación de parcelas.",
            )
        ]
    )
    assert records[0]["user_input"].startswith("¿Qué")
    assert records[0]["retrieved_contexts"]


def test_aggregate_ragas_scores():
    metrics = aggregate_ragas_scores(
        [
            {
                "faithfulness": 0.8,
                "answer_relevancy": 0.6,
                "context_precision": 0.5,
                "context_recall": 1.0,
            },
            {
                "faithfulness": 0.4,
                "answer_relevancy": 0.8,
                "context_precision": 0.5,
                "context_recall": 0.0,
            },
        ]
    )
    assert metrics["faithfulness"] == pytest.approx(0.6)
    assert metrics["context_recall"] == pytest.approx(0.5)


def test_run_ragas_evaluation_with_injected_evaluator():
    def fake_evaluator(records):
        return [
            {
                **records[0],
                "faithfulness": 0.9,
                "answer_relevancy": 0.8,
                "context_precision": 0.7,
                "context_recall": 0.6,
            }
        ]

    result = run_ragas_evaluation(
        [
            RagasSample(
                user_input="q",
                retrieved_contexts=["c"],
                response="r",
                reference="ref",
            )
        ],
        evaluator=fake_evaluator,
    )
    assert result["source"] == "ragas"
    assert result["count"] == 1
    assert result["metrics"]["faithfulness"] == 0.9


def test_run_ragas_evaluation_empty():
    result = run_ragas_evaluation([])
    assert result["count"] == 0
    assert result["metrics"]["faithfulness"] == 0.0
