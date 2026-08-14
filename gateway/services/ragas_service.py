"""Integración RAGAS para evaluación del pipeline RAG."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional


RAGAS_METRICS = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)


@dataclass
class RagasSample:
    user_input: str
    retrieved_contexts: list[str]
    response: str
    reference: Optional[str] = None


def build_ragas_records(samples: list[RagasSample]) -> list[dict[str, Any]]:
    """Normaliza muestras al contrato esperado por RAGAS/EvaluationDataset."""
    records: list[dict[str, Any]] = []
    for sample in samples:
        records.append(
            {
                "user_input": sample.user_input,
                "retrieved_contexts": list(sample.retrieved_contexts or []),
                "response": sample.response,
                "reference": sample.reference or "",
            }
        )
    return records


def aggregate_ragas_scores(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Calcula medias por métrica RAGAS a partir de filas individuales."""
    totals: dict[str, list[float]] = {m: [] for m in RAGAS_METRICS}
    for row in rows:
        for metric in RAGAS_METRICS:
            value = row.get(metric)
            if value is None:
                continue
            totals[metric].append(float(value))
    return {
        metric: (sum(values) / len(values) if values else 0.0)
        for metric, values in totals.items()
    }


def run_ragas_evaluation(
    samples: list[RagasSample],
    *,
    evaluator: Optional[Callable[[list[dict[str, Any]]], list[dict[str, Any]]]] = None,
) -> dict[str, Any]:
    """
    Ejecuta RAGAS.

    `evaluator` es inyectable para tests. En producción se enlaza con ragas.evaluate.
    """
    records = build_ragas_records(samples)
    if not records:
        return {
            "source": "ragas",
            "count": 0,
            "metrics": {m: 0.0 for m in RAGAS_METRICS},
            "rows": [],
        }

    if evaluator is None:
        evaluator = _default_ragas_evaluator

    rows = evaluator(records)
    return {
        "source": "ragas",
        "count": len(rows),
        "metrics": aggregate_ragas_scores(rows),
        "rows": rows,
    }


def _default_ragas_evaluator(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Adaptador runtime a RAGAS.

    Se importa de forma diferida para no romper tests unitarios sin stack completo.
    """
    try:
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
        from datasets import Dataset
    except Exception as exc:  # pragma: no cover - depende del entorno
        raise RuntimeError(
            "RAGAS no está disponible en este entorno. "
            "Instala ragas/datasets o inyecta un evaluator."
        ) from exc

    dataset = Dataset.from_list(records)
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )
    # ragas puede devolver DataFrame-like o dict
    if hasattr(result, "to_pandas"):
        frame = result.to_pandas()
        return frame.to_dict(orient="records")
    if isinstance(result, dict):
        # Resultado agregado: expandir a una fila sintética
        return [
            {
                "user_input": records[0]["user_input"],
                "faithfulness": float(result.get("faithfulness", 0) or 0),
                "answer_relevancy": float(result.get("answer_relevancy", 0) or 0),
                "context_precision": float(result.get("context_precision", 0) or 0),
                "context_recall": float(result.get("context_recall", 0) or 0),
            }
        ]
    raise RuntimeError("Formato de resultado RAGAS no soportado")
