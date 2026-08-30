"""Tests de la métrica binaria de alucinación."""

from __future__ import annotations

import pytest

from evaluation.hallucination import (
    decide_is_hallucination,
    faithfulness_implies_hallucination,
    looks_like_abstention,
    parse_judge_hallucination_payload,
)

pytestmark = pytest.mark.unit


def test_abstention_is_not_hallucination():
    result = decide_is_hallucination(
        answer="No hay evidencia en el contexto para responder.",
        contexts=["El plátano se cultiva en Canarias."],
        judge_is_hallucination=True,
        faithfulness=0.1,
    )
    assert result["is_hallucination"] is False
    assert result["reason"] == "abstention"


def test_judge_and_low_faithfulness_mark_hallucination():
    result = decide_is_hallucination(
        answer="La finca produce 9999 toneladas diarias.",
        contexts=["La finca tiene 2 hectáreas de plátano."],
        judge_is_hallucination=True,
        faithfulness=0.2,
    )
    assert result["is_hallucination"] is True
    assert "judge" in result["reason"]
    assert "faithfulness" in result["reason"]
    assert "9999" in result["unsupported_claims"]


def test_grounded_answer():
    result = decide_is_hallucination(
        answer="La finca tiene 2 hectáreas.",
        contexts=["La finca tiene 2 hectáreas de plátano."],
        judge_is_hallucination=False,
        faithfulness=0.9,
    )
    assert result["is_hallucination"] is False
    assert result["reason"] == "grounded"


def test_faithfulness_threshold():
    assert faithfulness_implies_hallucination(0.49) is True
    assert faithfulness_implies_hallucination(0.5) is False
    assert looks_like_abstention("") is True


def test_parse_judge_payload():
    raw = """```json
    {"is_hallucination": true, "confidence": 0.8, "unsupported_claims": ["X"]}
    ```"""
    parsed = parse_judge_hallucination_payload(raw)
    assert parsed["is_hallucination"] is True
    assert parsed["unsupported_claims"] == ["X"]
