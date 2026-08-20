"""Catálogo, persistencia y ejecución del laboratorio configurable."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
from collections import defaultdict
from typing import Any

from fastapi import HTTPException
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.evaluation_metrics import (
    citation_accuracy,
    ndcg_at_k,
    numeric_match,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from services.hallucination_metric import decide_is_hallucination
from services.ragas_service import RAGAS_METRICS, RagasSample, run_ragas_evaluation
from rag.adapters.outbound.ollama import RAG_TEMPERATURE

RAG_FIELDS = (
    "traceId",
    "prompt",
    "context",
    "response",
    "timestamp",
    "expected_response",
    "expected_context",
    "metadata",
    "pipeline",
    "alternate_response",
    "code_hash",
)

METRIC_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": "faithfulness",
        "name": "Fidelidad al boletín",
        "description": "Comprueba si el consejo agrícola está respaldado por la normativa o ficha recuperada.",
        "category": "response",
        "required_fields": ["context", "response"],
        "default_threshold": {"operator": "gte", "value": 0.7},
        "engine": "ragas",
    },
    {
        "id": "answer_relevancy",
        "name": "Pertinencia agraria",
        "description": "Mide si la respuesta atiende al cultivo, parcela o trámite preguntado, sin relleno.",
        "category": "response",
        "required_fields": ["prompt", "response"],
        "default_threshold": {"operator": "gte", "value": 0.7},
        "engine": "ragas",
    },
    {
        "id": "context_precision",
        "name": "Precisión de contexto",
        "description": "Evalúa cuánto del contexto recuperado (PAC, POSEI, fitosanitario) resulta útil.",
        "category": "context",
        "required_fields": ["prompt", "context", "expected_response"],
        "default_threshold": {"operator": "gte", "value": 0.6},
        "engine": "ragas",
    },
    {
        "id": "context_recall",
        "name": "Cobertura de contexto",
        "description": "Evalúa si el contexto cubre la respuesta de referencia del agricultor.",
        "category": "context",
        "required_fields": ["context", "expected_response"],
        "default_threshold": {"operator": "gte", "value": 0.6},
        "engine": "ragas",
    },
    {
        "id": "hallucination",
        "name": "Ausencia de alucinación",
        "description": "Detecta consejos no respaldados (dosis, plazos, ayudas). 1 significa respuesta segura.",
        "category": "response",
        "required_fields": ["context", "response"],
        "default_threshold": {"operator": "gte", "value": 1.0},
        "engine": "hallucination",
    },
    {
        "id": "numeric_match",
        "name": "Dosis y cifras",
        "description": "Compara importes, dosis y hectáreas entre la respuesta y la referencia.",
        "category": "response",
        "required_fields": ["response", "expected_response"],
        "default_threshold": {"operator": "gte", "value": 1.0},
        "engine": "deterministic",
    },
    {
        "id": "citation_accuracy",
        "name": "Precisión de citas",
        "description": "Valida las citas del consejo frente a boletines y fichas recuperadas.",
        "category": "text",
        "required_fields": ["response", "context"],
        "default_threshold": {"operator": "gte", "value": 0.8},
        "engine": "deterministic",
    },
    {
        "id": "retrieval_precision",
        "name": "Precisión retrieval",
        "description": "Compara los fragmentos recuperados con los esperados para la pregunta agraria.",
        "category": "context",
        "required_fields": ["context", "expected_context"],
        "default_threshold": {"operator": "gte", "value": 0.6},
        "engine": "retrieval",
    },
    {
        "id": "retrieval_recall",
        "name": "Recall retrieval",
        "description": "Mide cuántos fragmentos esperados (normativa, ficha, parcela) fueron recuperados.",
        "category": "context",
        "required_fields": ["context", "expected_context"],
        "default_threshold": {"operator": "gte", "value": 0.6},
        "engine": "retrieval",
    },
    {
        "id": "mrr",
        "name": "MRR (fuentes)",
        "description": "Posición del primer fragmento relevante para la consulta del agricultor.",
        "category": "context",
        "required_fields": ["context", "expected_context"],
        "default_threshold": {"operator": "gte", "value": 0.5},
        "engine": "retrieval",
    },
    {
        "id": "ndcg",
        "name": "nDCG (orden)",
        "description": "Calidad del orden de las fuentes recuperadas (boletines, PAC, fichas).",
        "category": "context",
        "required_fields": ["context", "expected_context"],
        "default_threshold": {"operator": "gte", "value": 0.6},
        "engine": "retrieval",
    },
)
CATALOG_BY_ID = {item["id"]: item for item in METRIC_CATALOG}


async def init_evaluation_lab_tables(db: AsyncSession) -> None:
    statements = (
        """CREATE TABLE IF NOT EXISTS rag_evaluation_configs (
             id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
             dataset_id uuid NOT NULL REFERENCES rag_datasets(id) ON DELETE CASCADE,
             organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
             tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
             knowledge_base_id uuid REFERENCES knowledge_bases(id) ON DELETE SET NULL,
             name varchar(255) NOT NULL, provider varchar(40) NOT NULL DEFAULT 'ollama',
             model_name varchar(255) NOT NULL DEFAULT 'llama3.2:latest',
             metrics jsonb NOT NULL DEFAULT '[]'::jsonb,
             mapping jsonb NOT NULL DEFAULT '{}'::jsonb,
             thresholds jsonb NOT NULL DEFAULT '{}'::jsonb,
             filters jsonb NOT NULL DEFAULT '{}'::jsonb,
             created_by uuid REFERENCES users(id) ON DELETE SET NULL,
             created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
             updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS rag_evaluation_runs (
             id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
             config_id uuid NOT NULL REFERENCES rag_evaluation_configs(id) ON DELETE CASCADE,
             dataset_id uuid NOT NULL REFERENCES rag_datasets(id) ON DELETE CASCADE,
             organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
             tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
             status varchar(30) NOT NULL DEFAULT 'running', fingerprint varchar(64) NOT NULL,
             parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
             aggregates jsonb NOT NULL DEFAULT '{}'::jsonb,
             row_count integer NOT NULL DEFAULT 0, passed_count integer NOT NULL DEFAULT 0,
             failed_count integer NOT NULL DEFAULT 0, error text,
             started_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, finished_at timestamptz)""",
        """CREATE TABLE IF NOT EXISTS rag_evaluation_results (
             id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
             run_id uuid NOT NULL REFERENCES rag_evaluation_runs(id) ON DELETE CASCADE,
             dataset_row_id uuid NOT NULL REFERENCES rag_dataset_rows(id) ON DELETE CASCADE,
             metric varchar(80) NOT NULL, value double precision, passed boolean NOT NULL DEFAULT false,
             explanation text, latency_ms double precision, details jsonb NOT NULL DEFAULT '{}'::jsonb,
             created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
             UNIQUE(run_id, dataset_row_id, metric))""",
    )
    for statement in statements:
        await db.execute(text(statement))
    await db.commit()


def _serialize(row: Any) -> dict[str, Any]:
    result = dict(row)
    for key, value in result.items():
        if hasattr(value, "isoformat"):
            result[key] = value.isoformat()
        elif key == "id" or key.endswith("_id"):
            result[key] = str(value) if value is not None else None
    return result


async def validate_dataset_access(
    db: AsyncSession, *, dataset_id: str, context: dict, require_department: bool = True
) -> dict[str, Any]:
    row = (
        (
            await db.execute(
                text("""SELECT rd.*, om.department_id
                   FROM rag_datasets rd
                   JOIN organization_members om
                     ON om.organization_id=rd.organization_id AND om.user_id=:user
                    AND om.active=true
                   WHERE rd.id=:dataset AND rd.organization_id=:org
                     AND rd.tenant_id=:tenant"""),
                {
                    "dataset": dataset_id,
                    "org": context["organization_id"],
                    "tenant": context["tenant_id"],
                    "user": context["user_id"],
                },
            )
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    role = str(context.get("role", "")).lower()
    if require_department and role not in {"admin", "super_admin", "org_admin"}:
        allowed = await db.scalar(
            text("""SELECT NOT EXISTS (
                       SELECT 1 FROM department_knowledge_bases
                       WHERE knowledge_base_id=:kb AND organization_id=:org
                   ) OR EXISTS (
                       SELECT 1 FROM department_knowledge_bases
                       WHERE knowledge_base_id=:kb AND organization_id=:org
                         AND department_id=:department
                   )"""),
            {
                "kb": row["knowledge_base_id"],
                "org": context["organization_id"],
                "department": row["department_id"],
            },
        )
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail="El dataset pertenece a departamentos no asociados al usuario",
            )
    return dict(row)


async def dataset_fields(db: AsyncSession, dataset_id: str, context: dict) -> list[str]:
    await validate_dataset_access(db, dataset_id=dataset_id, context=context)
    row = (
        (
            await db.execute(
                text("""SELECT
                    bool_or("traceId" IS NOT NULL) AS "traceId",
                    bool_or(prompt IS NOT NULL AND prompt <> '') AS prompt,
                    bool_or(context IS NOT NULL AND context <> 'null'::jsonb) AS context,
                    bool_or(response IS NOT NULL AND response <> '') AS response,
                    bool_or(timestamp IS NOT NULL) AS timestamp,
                    bool_or(expected_response IS NOT NULL AND expected_response <> '') AS expected_response,
                    bool_or(expected_context IS NOT NULL AND expected_context <> 'null'::jsonb) AS expected_context,
                    bool_or(metadata IS NOT NULL AND metadata <> '{}'::jsonb) AS metadata,
                    bool_or(pipeline IS NOT NULL AND pipeline <> 'null'::jsonb) AS pipeline,
                    bool_or(alternate_response IS NOT NULL AND alternate_response <> '') AS alternate_response,
                    bool_or(code_hash IS NOT NULL) AS code_hash
                   FROM rag_dataset_rows WHERE dataset_id=:dataset"""),
                {"dataset": dataset_id},
            )
        )
        .mappings()
        .first()
    )
    return [field for field in RAG_FIELDS if row and row.get(field)]


def validate_definition(payload: dict[str, Any], available_fields: list[str]) -> None:
    unknown = [metric for metric in payload["metrics"] if metric not in CATALOG_BY_ID]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Métricas desconocidas: {unknown}")
    mapping = payload.get("mapping") or {}
    missing: dict[str, list[str]] = {}
    for metric_id in payload["metrics"]:
        required = CATALOG_BY_ID[metric_id]["required_fields"]
        absent = [
            requirement
            for requirement in required
            if mapping.get(requirement, requirement) not in available_fields
        ]
        if absent:
            missing[metric_id] = absent
    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "El dataset no contiene los campos requeridos",
                "missing": missing,
            },
        )


async def list_configs(db: AsyncSession, dataset_id: str, context: dict) -> list[dict]:
    await validate_dataset_access(db, dataset_id=dataset_id, context=context)
    rows = (
        (
            await db.execute(
                text("""SELECT * FROM rag_evaluation_configs
                   WHERE dataset_id=:dataset AND organization_id=:org AND tenant_id=:tenant
                   ORDER BY updated_at DESC"""),
                {
                    "dataset": dataset_id,
                    "org": context["organization_id"],
                    "tenant": context["tenant_id"],
                },
            )
        )
        .mappings()
        .all()
    )
    return [_serialize(row) for row in rows]


async def create_config(
    db: AsyncSession, payload: dict[str, Any], context: dict
) -> dict[str, Any]:
    dataset = await validate_dataset_access(
        db, dataset_id=payload["dataset_id"], context=context
    )
    fields = await dataset_fields(db, payload["dataset_id"], context)
    validate_definition(payload, fields)
    row = (
        (
            await db.execute(
                text("""INSERT INTO rag_evaluation_configs
                   (dataset_id, organization_id, tenant_id, knowledge_base_id, name,
                    provider, model_name, metrics, mapping, thresholds, filters, created_by)
                   VALUES (:dataset, :org, :tenant, :kb, :name, 'ollama', :model,
                           CAST(:metrics AS jsonb), CAST(:mapping AS jsonb),
                           CAST(:thresholds AS jsonb), CAST(:filters AS jsonb), :user)
                   RETURNING *"""),
                {
                    "dataset": payload["dataset_id"],
                    "org": context["organization_id"],
                    "tenant": context["tenant_id"],
                    "kb": dataset["knowledge_base_id"],
                    "name": payload["name"],
                    "model": payload["model_name"],
                    "metrics": json.dumps(payload["metrics"]),
                    "mapping": json.dumps(payload.get("mapping") or {}),
                    "thresholds": json.dumps(payload.get("thresholds") or {}),
                    "filters": json.dumps(payload.get("filters") or {}),
                    "user": context["user_id"],
                },
            )
        )
        .mappings()
        .one()
    )
    await db.commit()
    return _serialize(row)


async def get_config(db: AsyncSession, config_id: str, context: dict) -> dict[str, Any]:
    row = (
        (
            await db.execute(
                text("""SELECT * FROM rag_evaluation_configs
                   WHERE id=:id AND organization_id=:org AND tenant_id=:tenant"""),
                {
                    "id": config_id,
                    "org": context["organization_id"],
                    "tenant": context["tenant_id"],
                },
            )
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    await validate_dataset_access(
        db, dataset_id=str(row["dataset_id"]), context=context
    )
    return _serialize(row)


async def update_config(
    db: AsyncSession, config_id: str, changes: dict[str, Any], context: dict
) -> dict[str, Any]:
    current = await get_config(db, config_id, context)
    merged = {
        **current,
        **{key: value for key, value in changes.items() if value is not None},
    }
    fields = await dataset_fields(db, current["dataset_id"], context)
    validate_definition(merged, fields)
    await db.execute(
        text("""UPDATE rag_evaluation_configs SET
               name=:name, model_name=:model, metrics=CAST(:metrics AS jsonb),
               mapping=CAST(:mapping AS jsonb), thresholds=CAST(:thresholds AS jsonb),
               filters=CAST(:filters AS jsonb), updated_at=CURRENT_TIMESTAMP
               WHERE id=:id"""),
        {
            "id": config_id,
            "name": merged["name"],
            "model": merged["model_name"],
            "metrics": json.dumps(merged["metrics"]),
            "mapping": json.dumps(merged["mapping"]),
            "thresholds": json.dumps(merged["thresholds"]),
            "filters": json.dumps(merged["filters"]),
        },
    )
    await db.commit()
    return await get_config(db, config_id, context)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    if isinstance(value, dict):
        return [str(item) for item in value.values() if item not in (None, "")]
    return [str(value)]


def _mapped(row: dict[str, Any], mapping: dict[str, str], field: str) -> Any:
    return row.get(mapping.get(field, field))


def _fallback_ragas(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for record in records:
        prompt = set(str(record["user_input"]).lower().split())
        answer = set(str(record["response"]).lower().split())
        context = set(" ".join(record["retrieved_contexts"]).lower().split())
        reference = set(str(record.get("reference") or "").lower().split())
        overlap_context = len(answer & context) / max(1, len(answer))
        relevance = len(answer & prompt) / max(1, len(prompt))
        recall = len(context & reference) / max(1, len(reference))
        output.append(
            {
                **record,
                "faithfulness": min(1.0, overlap_context),
                "answer_relevancy": min(1.0, relevance),
                "context_precision": min(1.0, recall),
                "context_recall": min(1.0, recall),
            }
        )
    return output


async def _ollama_ragas_scores(
    samples: list[RagasSample], model_name: str
) -> list[dict[str, Any]]:
    """Juez local compatible con las cuatro salidas RAGAS, sin proveedores cloud."""
    base_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    semaphore = asyncio.Semaphore(4)

    async def evaluate(sample: RagasSample) -> dict[str, Any]:
        prompt = f"""Evalúa esta muestra RAG con puntuaciones entre 0 y 1.
Devuelve exclusivamente JSON con las claves faithfulness, answer_relevancy,
context_precision y context_recall.
Pregunta: {sample.user_input}
Contextos: {json.dumps(sample.retrieved_contexts, ensure_ascii=False)}
Respuesta: {sample.response}
Referencia: {sample.reference or ""}
"""
        async with semaphore:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{base_url}/api/chat",
                    json={
                        "model": model_name,
                        "stream": False,
                        "format": "json",
                        "messages": [{"role": "user", "content": prompt}],
                        "options": {"temperature": RAG_TEMPERATURE},
                    },
                )
                response.raise_for_status()
        content = response.json().get("message", {}).get("content", "{}")
        content = re.sub(r"^```(?:json)?|```$", "", content.strip()).strip()
        data = json.loads(content)
        return {
            "user_input": sample.user_input,
            "retrieved_contexts": sample.retrieved_contexts,
            "response": sample.response,
            "reference": sample.reference or "",
            **{
                metric: max(0.0, min(1.0, float(data.get(metric, 0) or 0)))
                for metric in RAGAS_METRICS
            },
        }

    return await asyncio.gather(*(evaluate(sample) for sample in samples))


def _fingerprint(config: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    payload = {
        "config": {
            key: config[key]
            for key in ("model_name", "metrics", "mapping", "thresholds", "filters")
        },
        "rows": [{field: row.get(field) for field in RAG_FIELDS} for row in rows],
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode()
    ).hexdigest()


async def run_config(
    db: AsyncSession, config_id: str, context: dict, *, force: bool = False
) -> dict[str, Any]:
    config = await get_config(db, config_id, context)
    filters = config.get("filters") or {}
    clauses = ["dataset_id=:dataset"]
    params: dict[str, Any] = {
        "dataset": config["dataset_id"],
        "limit": min(int(filters.get("limit", 100)), 500),
    }
    statuses = list(filters.get("statuses") or [])
    if statuses:
        clauses.append("status = ANY(:statuses)")
        params["statuses"] = statuses
    rows = [
        dict(row)
        for row in (
            await db.execute(
                text(f"""SELECT * FROM rag_dataset_rows
                        WHERE {' AND '.join(clauses)}
                        ORDER BY created_at, id LIMIT :limit"""),
                params,
            )
        )
        .mappings()
        .all()
    ]
    categories = set(filters.get("categories") or [])
    split = filters.get("split", "all")
    if categories:
        rows = [
            row
            for row in rows
            if str((row.get("metadata") or {}).get("category", "")) in categories
        ]
    if split != "all":
        rows = [
            row
            for row in rows
            if str((row.get("metadata") or {}).get("split", "dev")) == split
        ]
    if not rows:
        raise HTTPException(
            status_code=422, detail="No hay filas que cumplan los filtros"
        )

    fingerprint = _fingerprint(config, rows)
    if not force:
        cached = (
            (
                await db.execute(
                    text("""SELECT * FROM rag_evaluation_runs
                       WHERE config_id=:config AND fingerprint=:fingerprint
                         AND status='completed' ORDER BY finished_at DESC LIMIT 1"""),
                    {"config": config_id, "fingerprint": fingerprint},
                )
            )
            .mappings()
            .first()
        )
        if cached:
            return {**_serialize(cached), "cached": True}

    run = (
        (
            await db.execute(
                text("""INSERT INTO rag_evaluation_runs
                   (config_id, dataset_id, organization_id, tenant_id, fingerprint, parameters)
                   VALUES (:config, :dataset, :org, :tenant, :fingerprint, CAST(:parameters AS jsonb))
                   RETURNING *"""),
                {
                    "config": config_id,
                    "dataset": config["dataset_id"],
                    "org": context["organization_id"],
                    "tenant": context["tenant_id"],
                    "fingerprint": fingerprint,
                    "parameters": json.dumps(
                        {
                            "provider": "ollama",
                            "model_name": config["model_name"],
                            "filters": filters,
                        }
                    ),
                },
            )
        )
        .mappings()
        .one()
    )
    await db.commit()

    mapping = config.get("mapping") or {}
    selected = list(config["metrics"])
    ragas_selected = [metric for metric in selected if metric in RAGAS_METRICS]
    ragas_rows: list[dict[str, Any]] = [{} for _ in rows]
    if ragas_selected:
        samples = [
            RagasSample(
                user_input=str(_mapped(row, mapping, "prompt") or ""),
                retrieved_contexts=_as_list(_mapped(row, mapping, "context")),
                response=str(_mapped(row, mapping, "response") or ""),
                reference=str(_mapped(row, mapping, "expected_response") or ""),
            )
            for row in rows
        ]
        try:
            ragas_rows = await _ollama_ragas_scores(samples, config["model_name"])
        except Exception:
            ragas_rows = (
                await asyncio.to_thread(
                    run_ragas_evaluation, samples, evaluator=_fallback_ragas
                )
            )["rows"]

    totals: dict[str, list[float]] = defaultdict(list)
    passed_rows = 0
    result_records: list[dict[str, Any]] = []
    thresholds = config.get("thresholds") or {}
    started = time.perf_counter()
    for index, row in enumerate(rows):
        contexts = _as_list(_mapped(row, mapping, "context"))
        expected_contexts = _as_list(_mapped(row, mapping, "expected_context"))
        answer = str(_mapped(row, mapping, "response") or "")
        expected_answer = str(_mapped(row, mapping, "expected_response") or "")
        values: dict[str, tuple[float, str, dict[str, Any]]] = {}
        for metric in ragas_selected:
            value = float(ragas_rows[index].get(metric) or 0.0)
            values[metric] = (value, "Resultado RAGAS", {})
        if "hallucination" in selected:
            faith = values.get("faithfulness", (None, "", {}))[0]
            detail = decide_is_hallucination(
                answer=answer,
                contexts=contexts,
                faithfulness=faith,
                faithfulness_threshold=float(
                    thresholds.get("faithfulness", {}).get("value", 0.5)
                ),
            )
            values["hallucination"] = (
                0.0 if detail["is_hallucination"] else 1.0,
                detail["reason"],
                detail,
            )
        if "numeric_match" in selected:
            values["numeric_match"] = (
                numeric_match(expected_answer, answer),
                "Comparación numérica determinista",
                {},
            )
        if "citation_accuracy" in selected:
            values["citation_accuracy"] = (
                citation_accuracy(answer, contexts),
                "Citas contrastadas con el contexto",
                {},
            )
        relevant, retrieved = set(expected_contexts), contexts
        retrieval_values = {
            "retrieval_precision": precision_at_k(relevant, retrieved, len(retrieved)),
            "retrieval_recall": recall_at_k(relevant, retrieved, len(retrieved)),
            "mrr": reciprocal_rank(relevant, retrieved),
            "ndcg": ndcg_at_k(relevant, retrieved, len(retrieved)),
        }
        for metric, value in retrieval_values.items():
            if metric in selected:
                values[metric] = (
                    value,
                    "Comparación de contextos esperados y recuperados",
                    {},
                )

        row_passed = True
        for metric in selected:
            value, explanation, details = values.get(metric, (0.0, "Sin resultado", {}))
            threshold = (
                thresholds.get(metric) or CATALOG_BY_ID[metric]["default_threshold"]
            )
            passed = (
                value >= float(threshold["value"])
                if threshold.get("operator", "gte") == "gte"
                else value <= float(threshold["value"])
            )
            row_passed = row_passed and passed
            totals[metric].append(value)
            result_records.append(
                {
                    "row_id": str(row["id"]),
                    "metric": metric,
                    "value": value,
                    "passed": passed,
                    "explanation": explanation,
                    "details": details,
                }
            )
        passed_rows += int(row_passed)

    for result in result_records:
        await db.execute(
            text("""INSERT INTO rag_evaluation_results
                   (run_id, dataset_row_id, metric, value, passed, explanation, latency_ms, details)
                   VALUES (:run, :row, :metric, :value, :passed, :explanation, :latency,
                           CAST(:details AS jsonb))"""),
            {
                **result,
                "run": str(run["id"]),
                "row": result["row_id"],
                "latency": (time.perf_counter() - started) * 1000 / max(1, len(rows)),
                "details": json.dumps(result["details"], default=str),
            },
        )
    aggregates = {
        metric: sum(values) / len(values) if values else 0.0
        for metric, values in totals.items()
    }
    await db.execute(
        text("""UPDATE rag_evaluation_runs SET status='completed',
               aggregates=CAST(:aggregates AS jsonb), row_count=:count,
               passed_count=:passed, failed_count=:failed, finished_at=CURRENT_TIMESTAMP
               WHERE id=:id"""),
        {
            "id": str(run["id"]),
            "aggregates": json.dumps(aggregates),
            "count": len(rows),
            "passed": passed_rows,
            "failed": len(rows) - passed_rows,
        },
    )
    await db.commit()
    return await get_run(db, str(run["id"]), context)


async def list_runs(
    db: AsyncSession, config_id: str, context: dict
) -> list[dict[str, Any]]:
    await get_config(db, config_id, context)
    rows = (
        (
            await db.execute(
                text("""SELECT * FROM rag_evaluation_runs
                   WHERE config_id=:config AND organization_id=:org AND tenant_id=:tenant
                   ORDER BY started_at DESC LIMIT 50"""),
                {
                    "config": config_id,
                    "org": context["organization_id"],
                    "tenant": context["tenant_id"],
                },
            )
        )
        .mappings()
        .all()
    )
    return [_serialize(row) for row in rows]


async def get_run(db: AsyncSession, run_id: str, context: dict) -> dict[str, Any]:
    row = (
        (
            await db.execute(
                text("""SELECT * FROM rag_evaluation_runs
                   WHERE id=:id AND organization_id=:org AND tenant_id=:tenant"""),
                {
                    "id": run_id,
                    "org": context["organization_id"],
                    "tenant": context["tenant_id"],
                },
            )
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Corrida no encontrada")
    results = (
        (
            await db.execute(
                text("""SELECT id, dataset_row_id, metric, value, passed, explanation,
                          latency_ms, details, created_at
                   FROM rag_evaluation_results WHERE run_id=:run
                   ORDER BY dataset_row_id, metric"""),
                {"run": run_id},
            )
        )
        .mappings()
        .all()
    )
    return {
        **_serialize(row),
        "cached": False,
        "results": [_serialize(result) for result in results],
    }
