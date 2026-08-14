from __future__ import annotations

import pytest
from fastapi import HTTPException

from schemas.evaluation import EvaluationLabConfigCreate
from services.evaluation_lab_service import (
    CATALOG_BY_ID,
    METRIC_CATALOG,
    _fallback_ragas,
    validate_definition,
)


def test_catalog_has_unique_metrics_and_required_fields():
    ids = [metric["id"] for metric in METRIC_CATALOG]
    assert len(ids) == len(set(ids))
    assert {"faithfulness", "context_precision", "hallucination", "mrr"} <= set(ids)
    assert all(metric["required_fields"] for metric in METRIC_CATALOG)


def test_config_deduplicates_metrics_and_forces_ollama():
    config = EvaluationLabConfigCreate(
        dataset_id="dataset-id",
        name="Calidad",
        metrics=["faithfulness", "faithfulness"],
    )
    assert config.provider == "ollama"
    assert config.metrics == ["faithfulness"]


def test_schema_compatibility_rejects_missing_fields():
    with pytest.raises(HTTPException) as exc:
        validate_definition(
            {
                "metrics": ["faithfulness"],
                "mapping": {"context": "context", "response": "response"},
            },
            ["context"],
        )
    assert exc.value.status_code == 422
    assert exc.value.detail["missing"]["faithfulness"] == ["response"]


def test_schema_mapping_can_redirect_required_fields():
    validate_definition(
        {
            "metrics": ["faithfulness"],
            "mapping": {
                "context": "expected_context",
                "response": "alternate_response",
            },
        },
        ["expected_context", "alternate_response"],
    )


def test_fallback_ragas_is_deterministic_and_bounded():
    rows = _fallback_ragas(
        [
            {
                "user_input": "producción plátano",
                "retrieved_contexts": ["la producción de plátano fue alta"],
                "response": "la producción fue alta",
                "reference": "producción alta",
            }
        ]
    )
    assert set(CATALOG_BY_ID).issuperset(
        {"faithfulness", "answer_relevancy", "context_precision", "context_recall"}
    )
    assert all(
        0 <= rows[0][metric] <= 1
        for metric in (
            "faithfulness",
            "answer_relevancy",
            "context_precision",
            "context_recall",
        )
    )
