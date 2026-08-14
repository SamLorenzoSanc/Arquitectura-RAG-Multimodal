"""Tests API de RAGAS + alucinación binaria."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from main import app
from services.ragas_service import run_ragas_evaluation

pytestmark = pytest.mark.api


def test_configurable_evaluation_routes_are_registered():
    contracts = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }
    assert {
        ("GET", "/api/v1/evaluation/catalog"),
        ("GET", "/api/v1/evaluation/configs"),
        ("POST", "/api/v1/evaluation/configs"),
        ("PUT", "/api/v1/evaluation/configs/{config_id}"),
        ("POST", "/api/v1/evaluation/configs/{config_id}/run"),
        ("GET", "/api/v1/evaluation/configs/{config_id}/runs"),
        ("GET", "/api/v1/evaluation/runs/{run_id}"),
    } <= contracts


def test_ragas_run_requires_auth(client):
    response = client.post("/api/v1/evaluation/ragas-run", json={"items": []})
    assert response.status_code in (401, 403, 422)


def test_ragas_run_with_fallback(authenticated_client):
    def fake_evaluator(records):
        return [
            {
                **records[0],
                "faithfulness": 0.2,
                "answer_relevancy": 0.3,
                "context_precision": 0.2,
                "context_recall": 0.1,
            }
        ]

    with patch(
        "routes.evaluation_ext.run_ragas_evaluation",
        side_effect=lambda samples, evaluator=None: run_ragas_evaluation(
            samples, evaluator=fake_evaluator
        ),
    ):
        response = authenticated_client.post(
            "/api/v1/evaluation/ragas-run",
            json={
                "items": [
                    {
                        "question": "¿Cuántas ha?",
                        "contexts": ["La finca tiene 2 hectáreas."],
                        "answer": "La finca produce 9999 toneladas.",
                        "reference": "2 hectáreas",
                    }
                ]
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "ragas+hallucination"
    assert body["count"] == 1
    assert body["rows"][0]["is_hallucination"] is True
