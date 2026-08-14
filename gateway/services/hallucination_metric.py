"""Métrica binaria de alucinación para auditoría RAG."""

from __future__ import annotations

import json
import re
from typing import Any, Optional


_ABSTENTION_MARKERS = (
    "no hay evidencia",
    "no se encuentra",
    "no dispongo de información",
    "no consta en el contexto",
    "no puedo responder",
    "insufficient context",
)


def looks_like_abstention(answer: str) -> bool:
    text = (answer or "").strip().lower()
    if not text:
        return True
    return any(marker in text for marker in _ABSTENTION_MARKERS)


def faithfulness_implies_hallucination(
    faithfulness: Optional[float],
    *,
    threshold: float = 0.5,
) -> bool:
    """Si faithfulness RAGAS está por debajo del umbral, se considera alucinación."""
    if faithfulness is None:
        return False
    return float(faithfulness) < threshold


def extract_unsupported_claims_heuristic(
    answer: str,
    contexts: list[str],
) -> list[str]:
    """
    Heurística determinista: números/fechas de la respuesta que no aparecen
    en el contexto se tratan como afirmaciones no soportadas.
    """
    joined = "\n".join(contexts or []).lower()
    answer_text = answer or ""
    claims: list[str] = []
    for match in re.findall(r"\b\d+(?:[.,]\d+)?\b", answer_text):
        token = match.replace(",", ".")
        # Buscar tanto con punto como con coma en contexto.
        if match.lower() not in joined and token not in joined:
            claims.append(match)
    return claims


def decide_is_hallucination(
    *,
    answer: str,
    contexts: list[str],
    judge_is_hallucination: Optional[bool] = None,
    faithfulness: Optional[float] = None,
    faithfulness_threshold: float = 0.5,
) -> dict[str, Any]:
    """
    Combina juez LLM (si existe), umbral RAGAS y heurística numérica.

    Regla:
    - abstención correcta => False
    - juez True => True
    - faithfulness bajo => True
    - heurística con claims no soportados => True
    """
    if looks_like_abstention(answer):
        return {
            "is_hallucination": False,
            "confidence": 0.9,
            "unsupported_claims": [],
            "reason": "abstention",
        }

    unsupported = extract_unsupported_claims_heuristic(answer, contexts)
    flags = []
    if judge_is_hallucination is True:
        flags.append("judge")
    if faithfulness_implies_hallucination(
        faithfulness, threshold=faithfulness_threshold
    ):
        flags.append("faithfulness")
    if unsupported:
        flags.append("unsupported_numbers")

    is_hallucination = bool(flags)
    confidence = 0.55
    if "judge" in flags and "faithfulness" in flags:
        confidence = 0.92
    elif "judge" in flags or "faithfulness" in flags:
        confidence = 0.8
    elif unsupported:
        confidence = 0.65

    return {
        "is_hallucination": is_hallucination,
        "confidence": confidence,
        "unsupported_claims": unsupported,
        "reason": "+".join(flags) if flags else "grounded",
    }


def parse_judge_hallucination_payload(raw: str) -> dict[str, Any]:
    """Parsea la respuesta JSON del juez de alucinación."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    data = json.loads(text)
    return {
        "is_hallucination": bool(data.get("is_hallucination")),
        "confidence": float(data.get("confidence", 0.5)),
        "unsupported_claims": list(data.get("unsupported_claims") or []),
    }
