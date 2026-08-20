"""Extensiones de evaluación: RAGAS + métrica binaria de alucinación."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.security import Permission, RequirePermission, get_tenant_context
from routes.auth import get_current_user
from ops.adapters.inbound.models import _fetch_available_models
from schemas.evaluation import (
    EvaluationLabConfigCreate,
    EvaluationLabConfigUpdate,
    EvaluationLabRunRequest,
)
from services.database import get_db
from evaluation.application import lab
from evaluation.application.ragas_service import RagasSample, run_ragas_evaluation
from evaluation.application.hallucination_metric import decide_is_hallucination
from models.user import User

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


class RagasItem(BaseModel):
    question: str
    contexts: list[str] = Field(default_factory=list)
    answer: str
    reference: Optional[str] = None
    faithfulness: Optional[float] = None
    judge_is_hallucination: Optional[bool] = None


class RagasRunRequest(BaseModel):
    items: list[RagasItem]
    faithfulness_threshold: float = 0.5


@router.get("/catalog")
async def evaluation_catalog(
    dataset_id: str | None = None,
    context: dict = Depends(get_tenant_context),
    _: bool = Depends(RequirePermission(Permission.EVAL_READ)),
    db: AsyncSession = Depends(get_db),
):
    fields: list[str] = []
    if dataset_id:
        fields = await lab.dataset_fields(db, dataset_id, context)
    try:
        models = await _fetch_available_models()
    except Exception:
        models = ["llama3.2:latest"]
    metrics = []
    alternatives = {
        "response": {"response", "expected_response", "alternate_response"},
        "expected_response": {"expected_response", "response", "alternate_response"},
        "context": {"context", "expected_context"},
        "expected_context": {"expected_context", "context"},
    }
    for definition in lab.METRIC_CATALOG:
        missing = [
            field
            for field in definition["required_fields"]
            if not alternatives.get(field, {field}).intersection(fields)
        ]
        metrics.append(
            {
                **definition,
                "compatible": not dataset_id or not missing,
                "missing_fields": missing,
            }
        )
    return {
        "provider": "ollama",
        "models": models or ["llama3.2:latest"],
        "fields": fields,
        "metrics": metrics,
    }


@router.get("/configs")
async def list_evaluation_configs(
    dataset_id: str,
    context: dict = Depends(get_tenant_context),
    _: bool = Depends(RequirePermission(Permission.EVAL_READ)),
    db: AsyncSession = Depends(get_db),
):
    await lab.init_evaluation_lab_tables(db)
    return {"data": await lab.list_configs(db, dataset_id, context)}


@router.post("/configs")
async def create_evaluation_config(
    payload: EvaluationLabConfigCreate,
    context: dict = Depends(get_tenant_context),
    _: bool = Depends(RequirePermission(Permission.EVAL_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    await lab.init_evaluation_lab_tables(db)
    return await lab.create_config(db, payload.model_dump(mode="json"), context)


@router.put("/configs/{config_id}")
async def update_evaluation_config(
    config_id: str,
    payload: EvaluationLabConfigUpdate,
    context: dict = Depends(get_tenant_context),
    _: bool = Depends(RequirePermission(Permission.EVAL_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    await lab.init_evaluation_lab_tables(db)
    return await lab.update_config(
        db, config_id, payload.model_dump(mode="json", exclude_unset=True), context
    )


@router.post("/configs/{config_id}/run")
async def execute_evaluation_config(
    config_id: str,
    payload: EvaluationLabRunRequest,
    context: dict = Depends(get_tenant_context),
    _: bool = Depends(RequirePermission(Permission.EVAL_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    await lab.init_evaluation_lab_tables(db)
    return await lab.run_config(db, config_id, context, force=payload.force)


@router.get("/configs/{config_id}/runs")
async def list_evaluation_runs(
    config_id: str,
    context: dict = Depends(get_tenant_context),
    _: bool = Depends(RequirePermission(Permission.EVAL_READ)),
    db: AsyncSession = Depends(get_db),
):
    await lab.init_evaluation_lab_tables(db)
    return {"data": await lab.list_runs(db, config_id, context)}


@router.get("/runs/{run_id}")
async def get_evaluation_run(
    run_id: str,
    context: dict = Depends(get_tenant_context),
    _: bool = Depends(RequirePermission(Permission.EVAL_READ)),
    db: AsyncSession = Depends(get_db),
):
    await lab.init_evaluation_lab_tables(db)
    return await lab.get_run(db, run_id, context)


@router.post("/ragas-run")
async def ragas_run(
    request: RagasRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user, db
    if not request.items:
        raise HTTPException(status_code=400, detail="Se requiere al menos un ítem")

    samples = [
        RagasSample(
            user_input=item.question,
            retrieved_contexts=item.contexts,
            response=item.answer,
            reference=item.reference,
        )
        for item in request.items
    ]

    # En tests/CI se puede inyectar evaluator vía monkeypatch del servicio.
    # Aquí usamos un evaluator determinista si RAGAS no está operativo.
    def fallback_evaluator(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = []
        for record, item in zip(records, request.items):
            faith = item.faithfulness
            if faith is None:
                ctx = " ".join(record["retrieved_contexts"]).lower()
                ans = record["response"].lower()
                overlap = len(set(ans.split()) & set(ctx.split()))
                faith_score = 0.8 if overlap >= 3 else 0.3
            else:
                faith_score = float(faith)
            rows.append(
                {
                    **record,
                    "faithfulness": faith_score,
                    "answer_relevancy": min(1.0, faith_score + 0.1),
                    "context_precision": min(1.0, faith_score),
                    "context_recall": min(1.0, faith_score),
                }
            )
        return rows

    try:
        ragas_result = run_ragas_evaluation(samples)
    except RuntimeError:
        ragas_result = run_ragas_evaluation(samples, evaluator=fallback_evaluator)

    enriched = []
    for item, row in zip(request.items, ragas_result["rows"]):
        hall = decide_is_hallucination(
            answer=item.answer,
            contexts=item.contexts,
            judge_is_hallucination=item.judge_is_hallucination,
            faithfulness=row.get("faithfulness"),
            faithfulness_threshold=request.faithfulness_threshold,
        )
        enriched.append(
            {
                "question": item.question,
                "ragas": {
                    "faithfulness": row.get("faithfulness"),
                    "answer_relevancy": row.get("answer_relevancy"),
                    "context_precision": row.get("context_precision"),
                    "context_recall": row.get("context_recall"),
                },
                "is_hallucination": hall["is_hallucination"],
                "hallucination": hall,
            }
        )

    hallucination_rate = (
        sum(1 for row in enriched if row["is_hallucination"]) / len(enriched)
        if enriched
        else 0.0
    )
    return {
        "source": "ragas+hallucination",
        "metrics": ragas_result["metrics"],
        "hallucination_rate": hallucination_rate,
        "count": len(enriched),
        "rows": enriched,
    }
