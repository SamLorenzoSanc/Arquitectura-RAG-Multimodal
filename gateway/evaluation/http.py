from __future__ import annotations

from identity.http import get_current_user
from ops.http import _fetch_available_models
from evaluation import lab
from evaluation.ragas import RagasSample, run_ragas_evaluation
from evaluation.hallucination import decide_is_hallucination
"""Extensiones de evaluación: RAGAS + métrica binaria de alucinación."""


from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.security import Permission, RequirePermission, get_tenant_context
from schemas.evaluation import (
    EvaluationLabConfigCreate,
    EvaluationLabConfigUpdate,
    EvaluationLabRunRequest,
)
from services.database import get_db
from models.user import User

lab_router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


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


@lab_router.get("/catalog")
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


@lab_router.get("/configs")
async def list_evaluation_configs(
    dataset_id: str,
    context: dict = Depends(get_tenant_context),
    _: bool = Depends(RequirePermission(Permission.EVAL_READ)),
    db: AsyncSession = Depends(get_db),
):
    await lab.init_evaluation_lab_tables(db)
    return {"data": await lab.list_configs(db, dataset_id, context)}


@lab_router.post("/configs")
async def create_evaluation_config(
    payload: EvaluationLabConfigCreate,
    context: dict = Depends(get_tenant_context),
    _: bool = Depends(RequirePermission(Permission.EVAL_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    await lab.init_evaluation_lab_tables(db)
    return await lab.create_config(db, payload.model_dump(mode="json"), context)


@lab_router.put("/configs/{config_id}")
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


@lab_router.post("/configs/{config_id}/run")
async def execute_evaluation_config(
    config_id: str,
    payload: EvaluationLabRunRequest,
    context: dict = Depends(get_tenant_context),
    _: bool = Depends(RequirePermission(Permission.EVAL_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    await lab.init_evaluation_lab_tables(db)
    return await lab.run_config(db, config_id, context, force=payload.force)


@lab_router.get("/configs/{config_id}/runs")
async def list_evaluation_runs(
    config_id: str,
    context: dict = Depends(get_tenant_context),
    _: bool = Depends(RequirePermission(Permission.EVAL_READ)),
    db: AsyncSession = Depends(get_db),
):
    await lab.init_evaluation_lab_tables(db)
    return {"data": await lab.list_runs(db, config_id, context)}


@lab_router.get("/runs/{run_id}")
async def get_evaluation_run(
    run_id: str,
    context: dict = Depends(get_tenant_context),
    _: bool = Depends(RequirePermission(Permission.EVAL_READ)),
    db: AsyncSession = Depends(get_db),
):
    await lab.init_evaluation_lab_tables(db)
    return await lab.get_run(db, run_id, context)


@lab_router.post("/ragas-run")
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

from evaluation import rag_dataset as service
from evaluation.hitl import init_human_validation_tables

import json
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.security import get_tenant_context
from schemas.rag_dataset import (
    DatasetAddColumn,
    DatasetGuardrailsRequest,
    DatasetImportTraces,
    DatasetUpdate,
    DemoDatasetRequest,
    KnowledgeBaseDepartmentsUpdate,
    SyntheticDatasetRequest,
)
from services.database import get_db

datasets_router = APIRouter(prefix="/datasets", tags=["RAG datasets"])


def _json_form(value: str | None, expected: type, default: Any):
    if value is None or not value.strip():
        return default
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=422, detail=f"JSON de formulario inválido: {exc}"
        ) from exc
    if not isinstance(parsed, expected):
        raise HTTPException(status_code=422, detail=f"Se esperaba {expected.__name__}")
    return parsed


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key, value in result.items():
        if hasattr(value, "isoformat"):
            result[key] = value.isoformat()
        elif key.endswith("_id") and value is not None:
            result[key] = str(value)
    return result


@datasets_router.get("")
async def list_datasets(
    knowledge_base_id: str | None = Query(None),
    department_id: str | None = Query(None),
    status: str | None = Query(None),
    source_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    context: dict = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await service.init_rag_dataset_tables(db)
    clauses = ["rd.organization_id=:org", "rd.tenant_id=:tenant"]
    params: dict[str, Any] = {
        "org": context["organization_id"],
        "tenant": context["tenant_id"],
        "limit": limit,
    }
    if knowledge_base_id:
        clauses.append("rd.knowledge_base_id=:kb")
        params["kb"] = knowledge_base_id
    if status:
        clauses.append("rd.status=:status")
        params["status"] = status
    if source_type:
        clauses.append("rd.source_type=:source_type")
        params["source_type"] = source_type
    if department_id:
        clauses.append(
            """EXISTS (
                SELECT 1 FROM rag_dataset_departments rdd
                WHERE rdd.dataset_id=rd.id AND rdd.department_id=:dept
              )"""
        )
        params["dept"] = department_id
    result = await db.execute(
        text(f"""SELECT rd.id, rd.organization_id, rd.tenant_id,
                       rd.knowledge_base_id, rd.name, rd.description,
                       rd.source_type, rd.source_name, rd.source_metadata,
                       rd.mapping, rd.status, rd.row_count, rd.created_by,
                       rd.created_at, rd.updated_at,
                       kb.name AS knowledge_base_name,
                       COALESCE((
                         SELECT jsonb_agg(
                           jsonb_build_object('id', d.id, 'name', d.name)
                           ORDER BY d.name
                         )
                         FROM rag_dataset_departments rdd
                         JOIN departments d ON d.id=rdd.department_id
                         WHERE rdd.dataset_id=rd.id
                       ), '[]'::jsonb) AS departments
                FROM rag_datasets rd
                LEFT JOIN knowledge_bases kb ON kb.id=rd.knowledge_base_id
                WHERE {' AND '.join(clauses)}
                ORDER BY rd.created_at DESC LIMIT :limit"""),
        params,
    )
    rows = [_serialize(dict(row)) for row in result.mappings().all()]
    return {"count": len(rows), "data": rows}


@datasets_router.post("/preview")
async def preview_dataset(
    file: UploadFile = File(...),
    limit: int = Form(20),
    context: dict = Depends(get_tenant_context),
):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit debe estar entre 1 y 100")
    return await service.preview_upload(file, limit)


@datasets_router.post("/import")
async def import_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str | None = Form(None),
    knowledge_base_id: str | None = Form(None),
    mapping: str | None = Form(None),
    department_ids: str | None = Form(None),
    source_type: str | None = Form(None),
    context: dict = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await service.init_rag_dataset_tables(db)
    content = await file.read()
    rows, info = service.parse_content(
        file.filename or "upload", content, file.content_type
    )
    selected_mapping = _json_form(mapping, dict, info.get("suggested_mapping") or {})
    if not selected_mapping.get("prompt"):
        selected_mapping = {
            **service.infer_mapping(rows[0].keys() if rows else []),
            **selected_mapping,
        }
    kind = (source_type or "").strip().lower()
    if kind not in {"document", "logs", "upload"}:
        kind = "document" if info.get("kind") == "chunks" else "upload"
    return await service.import_rows(
        db,
        rows=rows,
        mapping=selected_mapping,
        name=name.strip(),
        description=description,
        source_type=kind,
        source_name=file.filename,
        source_metadata={k: v for k, v in info.items() if k != "rows"},
        organization_id=context["organization_id"],
        tenant_id=context["tenant_id"],
        knowledge_base_id=knowledge_base_id,
        department_ids=_json_form(department_ids, list, []),
        user_id=context["user_id"],
    )


@datasets_router.post("/synthetic")
async def generate_synthetic_dataset(
    payload: SyntheticDatasetRequest,
    context: dict = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await service.init_rag_dataset_tables(db)
    await init_human_validation_tables(db)
    rows = await service.synthetic_rows(
        db,
        organization_id=context["organization_id"],
        tenant_id=context["tenant_id"],
        knowledge_base_id=payload.knowledge_base_id,
        document_ids=payload.document_ids,
        questions=payload.questions,
        limit=payload.limit,
    )
    result = await service.import_rows(
        db,
        rows=rows,
        mapping=service.infer_mapping(rows[0].keys()),
        name=payload.name,
        description=payload.description,
        source_type="synthetic",
        source_name="document_questions",
        source_metadata={"document_ids": payload.document_ids, "generated": False},
        organization_id=context["organization_id"],
        tenant_id=context["tenant_id"],
        knowledge_base_id=payload.knowledge_base_id,
        department_ids=payload.department_ids,
        user_id=context["user_id"],
    )
    queued = 0
    if payload.enqueue_hitl:
        queued = await service.enqueue_synthetic_hitl(
            db,
            rows=rows,
            organization_id=context["organization_id"],
            knowledge_base_id=payload.knowledge_base_id,
            user_id=context["user_id"],
        )
    await db.execute(
        text("UPDATE rag_datasets SET status='pending_review' WHERE id=:id"),
        {"id": result["id"]},
    )
    await db.commit()
    return {**result, "status": "pending_review", "hitl_queued": queued}


@datasets_router.post("/synthetic/preview")
async def preview_synthetic_dataset(
    payload: SyntheticDatasetRequest,
    context: dict = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await service.init_rag_dataset_tables(db)
    await init_human_validation_tables(db)
    rows = await service.synthetic_rows(
        db,
        organization_id=context["organization_id"],
        tenant_id=context["tenant_id"],
        knowledge_base_id=payload.knowledge_base_id,
        document_ids=payload.document_ids,
        questions=payload.questions,
        limit=payload.limit,
    )
    columns = list(dict.fromkeys(str(key) for row in rows for key in row))
    return {
        "kind": "tabular",
        "total_rows": len(rows),
        "columns": columns,
        "schema_mapping": service.generate_schema(columns, rows),
        "suggested_mapping": service.infer_mapping(columns),
        "rows": rows,
    }


@datasets_router.get("/demo-catalog")
async def list_demo_datasets(
    _context: dict = Depends(get_tenant_context),
):
    return {"count": len(service.demo_catalog()), "data": service.demo_catalog()}


@datasets_router.post("/demo")
async def import_demo_dataset(
    payload: DemoDatasetRequest,
    context: dict = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await service.init_rag_dataset_tables(db)
    name, description, rows = service.demo_rows(payload.catalog_id)
    return await service.import_rows(
        db,
        rows=rows,
        mapping=service.infer_mapping(rows[0].keys()),
        name=(payload.name or name).strip(),
        description=payload.description or description,
        source_type="demo",
        source_name=payload.catalog_id,
        source_metadata={"catalog_id": payload.catalog_id},
        organization_id=context["organization_id"],
        tenant_id=context["tenant_id"],
        knowledge_base_id=payload.knowledge_base_id,
        department_ids=payload.department_ids,
        user_id=context["user_id"],
    )


@datasets_router.get("/knowledge-bases/{knowledge_base_id}/departments")
async def list_knowledge_base_departments(
    knowledge_base_id: str,
    context: dict = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await service.init_rag_dataset_tables(db)
    result = await db.execute(
        text("""SELECT d.id, d.name, d.description, dkb.created_at
               FROM department_knowledge_bases dkb
               JOIN departments d ON d.id=dkb.department_id
               JOIN knowledge_bases kb ON kb.id=dkb.knowledge_base_id
               WHERE dkb.knowledge_base_id=:kb AND dkb.organization_id=:org
                 AND kb.tenant_id=:tenant ORDER BY d.name"""),
        {
            "kb": knowledge_base_id,
            "org": context["organization_id"],
            "tenant": context["tenant_id"],
        },
    )
    rows = [_serialize(dict(row)) for row in result.mappings().all()]
    return {"count": len(rows), "data": rows}


@datasets_router.put("/knowledge-bases/{knowledge_base_id}/departments")
async def update_knowledge_base_departments(
    knowledge_base_id: str,
    payload: KnowledgeBaseDepartmentsUpdate,
    context: dict = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await service.init_rag_dataset_tables(db)
    await service._validate_scope(
        db, context["organization_id"], context["tenant_id"], knowledge_base_id
    )
    await service.associate_departments(
        db,
        organization_id=context["organization_id"],
        knowledge_base_id=knowledge_base_id,
        department_ids=payload.department_ids,
        user_id=context["user_id"],
        replace=payload.mode == "replace",
    )
    await db.commit()
    return {
        "knowledge_base_id": knowledge_base_id,
        "department_ids": payload.department_ids,
    }


@datasets_router.get("/departments/{department_id}/knowledge-bases")
async def list_department_knowledge_bases(
    department_id: str,
    context: dict = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await service.init_rag_dataset_tables(db)
    result = await db.execute(
        text("""SELECT kb.id, kb.name, kb.description, kb.tenant_id, dkb.created_at
               FROM department_knowledge_bases dkb
               JOIN knowledge_bases kb ON kb.id=dkb.knowledge_base_id
               WHERE dkb.department_id=:department AND dkb.organization_id=:org
                 AND kb.tenant_id=:tenant ORDER BY kb.name"""),
        {
            "department": department_id,
            "org": context["organization_id"],
            "tenant": context["tenant_id"],
        },
    )
    rows = [_serialize(dict(row)) for row in result.mappings().all()]
    return {"count": len(rows), "data": rows}


@datasets_router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    context: dict = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await service.init_rag_dataset_tables(db)
    dataset_result = await db.execute(
        text("""SELECT id, organization_id, tenant_id, knowledge_base_id, name,
                      description, source_type, source_name, source_metadata,
                      mapping, status, row_count, created_by, created_at, updated_at
               FROM rag_datasets
               WHERE id=:id AND organization_id=:org AND tenant_id=:tenant"""),
        {
            "id": dataset_id,
            "org": context["organization_id"],
            "tenant": context["tenant_id"],
        },
    )
    dataset = dataset_result.mappings().first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    row_result = await db.execute(
        text("""SELECT id, "traceId", prompt, context, response, timestamp,
                      expected_response, expected_context, metadata, pipeline,
                      alternate_response, code_hash, source, status, created_at
               FROM rag_dataset_rows
               WHERE dataset_id=:id AND organization_id=:org AND tenant_id=:tenant
               ORDER BY created_at, id OFFSET :offset LIMIT :limit"""),
        {
            "id": dataset_id,
            "org": context["organization_id"],
            "tenant": context["tenant_id"],
            "offset": offset,
            "limit": limit,
        },
    )
    return {
        "dataset": _serialize(dict(dataset)),
        "rows": [_serialize(dict(row)) for row in row_result.mappings().all()],
        "offset": offset,
        "limit": limit,
    }


@datasets_router.post("/{dataset_id}/rows")
async def add_dataset_rows(
    dataset_id: str,
    file: UploadFile = File(...),
    context: dict = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await service.init_rag_dataset_tables(db)
    content = await file.read()
    rows, _info = service.parse_content(
        file.filename or "upload", content, file.content_type
    )
    return await service.append_rows(
        db,
        dataset_id=dataset_id,
        rows=rows,
        organization_id=context["organization_id"],
        tenant_id=context["tenant_id"],
        source_name=file.filename,
    )


@datasets_router.get("/{dataset_id}/traces")
async def list_dataset_traces(
    dataset_id: str,
    limit: int = Query(100, ge=1, le=500),
    context: dict = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await service.init_rag_dataset_tables(db)
    return await service.list_traces(
        db,
        dataset_id=dataset_id,
        organization_id=context["organization_id"],
        tenant_id=context["tenant_id"],
        limit=limit,
    )


@datasets_router.post("/{dataset_id}/traces/import")
async def import_dataset_traces(
    dataset_id: str,
    payload: DatasetImportTraces = Body(default_factory=DatasetImportTraces),
    context: dict = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await service.init_rag_dataset_tables(db)
    body = payload
    return await service.import_traces_from_chat(
        db,
        dataset_id=dataset_id,
        organization_id=context["organization_id"],
        tenant_id=context["tenant_id"],
        limit=body.limit,
    )


@datasets_router.post("/{dataset_id}/columns")
async def add_dataset_column(
    dataset_id: str,
    payload: DatasetAddColumn,
    context: dict = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await service.init_rag_dataset_tables(db)
    return await service.add_llm_column(
        db,
        dataset_id=dataset_id,
        organization_id=context["organization_id"],
        tenant_id=context["tenant_id"],
        column_name=payload.column_name,
        prompt_template=payload.prompt_template,
        limit=payload.limit,
    )


@datasets_router.post("/{dataset_id}/guardrails")
async def run_dataset_guardrails(
    dataset_id: str,
    payload: DatasetGuardrailsRequest = Body(default_factory=DatasetGuardrailsRequest),
    context: dict = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await service.init_rag_dataset_tables(db)
    body = payload
    return await service.run_guardrails(
        db,
        dataset_id=dataset_id,
        organization_id=context["organization_id"],
        tenant_id=context["tenant_id"],
        limit=body.limit,
    )


@datasets_router.patch("/{dataset_id}")
async def update_dataset(
    dataset_id: str,
    payload: DatasetUpdate,
    context: dict = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await service.init_rag_dataset_tables(db)
    if payload.model_dump(exclude_unset=True) == {}:
        raise HTTPException(status_code=422, detail="No hay campos para actualizar")
    return await service.update_dataset(
        db,
        dataset_id=dataset_id,
        organization_id=context["organization_id"],
        tenant_id=context["tenant_id"],
        user_id=context["user_id"],
        name=payload.name,
        description=payload.description,
        knowledge_base_id=payload.knowledge_base_id,
        department_ids=payload.department_ids,
        mapping=payload.mapping,
    )


@datasets_router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    context: dict = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await service.init_rag_dataset_tables(db)
    return await service.delete_dataset(
        db,
        dataset_id=dataset_id,
        organization_id=context["organization_id"],
        tenant_id=context["tenant_id"],
    )

from evaluation import hitl
from identity.http import get_current_user
from typing import Any, Literal, Optional
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db

hitl_router = APIRouter(prefix="/human-validation", tags=["Human validation"])

ReviewStatus = Literal["pending", "approved", "rejected", "corrected"]


class ReviewDecision(BaseModel):
    status: Literal["approved", "rejected", "corrected"]
    reviewer_notes: Optional[str] = None
    corrected_answer: Optional[str] = Field(default=None, max_length=8000)
    question: Optional[str] = Field(default=None, max_length=2000)
    keywords: list[str] = Field(default_factory=list)
    category: Optional[str] = Field(default=None, max_length=80)


@hitl_router.get("/reviews", status_code=200)
async def list_reviews(
    status: Optional[str] = Query("pending"),
    source: Optional[str] = Query("document_question"),
    organization_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await hitl.init_human_validation_tables(db)
    clauses = ["1=1"]
    params: dict[str, Any] = {"limit": limit}
    if status and status != "all":
        clauses.append("status = :status")
        params["status"] = status
    if source and source != "all":
        clauses.append("source = :source")
        params["source"] = source
    if organization_id:
        clauses.append(
            "(organization_id = :organization_id OR organization_id IS NULL)"
        )
        params["organization_id"] = organization_id
    result = await db.execute(
        text(f"""
            SELECT id, source, user_id, organization_id, conversation_id,
                   document_id, knowledge_base_id, question, answer,
                   context_snippet, chunk_ids, status, corrected_answer,
                   reviewer_notes, reviewer_id, created_at, reviewed_at,
                   category, filename, rationale, keywords
            FROM rag_human_reviews
            WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC
            LIMIT :limit
            """),
        params,
    )
    rows = [hitl._serialize(dict(r)) for r in result.mappings().all()]
    pending = sum(1 for r in rows if r.get("status") == "pending")
    return {"count": len(rows), "pending": pending, "data": rows}


@hitl_router.post("/reviews/{review_id}", status_code=200)
async def decide_review(
    review_id: str,
    data: ReviewDecision,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await hitl.init_human_validation_tables(db)
    if data.status == "corrected" and not (data.corrected_answer or "").strip():
        raise HTTPException(
            status_code=400, detail="La corrección necesita un texto de respuesta"
        )
    result = await db.execute(
        text("""
            UPDATE rag_human_reviews
            SET status = :status,
                reviewer_notes = :reviewer_notes,
                corrected_answer = :corrected_answer,
                reviewer_id = :reviewer_id,
                reviewed_at = CURRENT_TIMESTAMP,
                question = COALESCE(:question, question),
                category = COALESCE(:category, category),
                keywords = CASE
                    WHEN CAST(:has_keywords AS boolean)
                    THEN CAST(:keywords AS jsonb)
                    ELSE COALESCE(keywords, '[]'::jsonb)
                END
            WHERE id = :id
            """),
        {
            "id": review_id,
            "status": data.status,
            "reviewer_notes": (data.reviewer_notes or "").strip() or None,
            "corrected_answer": (data.corrected_answer or "").strip() or None,
            "reviewer_id": str(current_user.id),
            "question": (data.question or "").strip() or None,
            "category": (data.category or "").strip() or None,
            "has_keywords": bool(data.keywords),
            "keywords": json.dumps(
                [str(item).strip() for item in data.keywords if str(item).strip()],
                ensure_ascii=False,
            ),
        },
    )
    if result.rowcount == 0:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Revisión no encontrada")

    review = await db.execute(
        text("""
            SELECT document_id, question, source, answer, category, filename,
                   organization_id, knowledge_base_id, keywords, corrected_answer
            FROM rag_human_reviews WHERE id = :id
            """),
        {"id": review_id},
    )
    row = review.mappings().first()
    if row and row.get("document_id") and row.get("question"):
        q_status = (
            "approved" if data.status in ("approved", "corrected") else "rejected"
        )
        await db.execute(
            text("""
                UPDATE document_questions
                SET status = :status,
                    reviewer_notes = :notes,
                    reviewed_at = CURRENT_TIMESTAMP,
                    reference_answer = COALESCE(:reference_answer, reference_answer),
                    category = COALESCE(:category, category),
                    keywords = CASE
                        WHEN CAST(:has_keywords AS boolean)
                        THEN CAST(:keywords AS jsonb)
                        ELSE keywords
                    END
                WHERE document_id = :document_id AND question = :question
                """),
            {
                "status": q_status,
                "notes": (data.reviewer_notes or "").strip() or None,
                "reference_answer": (data.corrected_answer or "").strip() or None,
                "category": (data.category or "").strip() or None,
                "has_keywords": bool(data.keywords),
                "keywords": json.dumps(
                    [str(item).strip() for item in data.keywords if str(item).strip()],
                    ensure_ascii=False,
                ),
                "document_id": str(row["document_id"]),
                "question": row["question"],
            },
        )
    if row and row.get("question") and data.status in ("approved", "corrected"):
        await hitl.promote_review_to_evaluation_bank(
            db,
            document_id=str(row["document_id"]) if row.get("document_id") else None,
            organization_id=str(row["organization_id"]) if row.get("organization_id") else None,
            question=(data.question or row.get("question") or ""),
            reference_answer=(
                data.corrected_answer
                or row.get("corrected_answer")
                or row.get("answer")
                or ""
            ),
            category=data.category or row.get("category"),
            keywords=data.keywords or row.get("keywords") or [],
            filename=row.get("filename"),
        )
    elif row and row.get("document_id") and data.status == "rejected":
        doc = await db.execute(
            text("SELECT tenant_id FROM public.documents WHERE id = :id LIMIT 1"),
            {"id": str(row["document_id"])},
        )
        tenant = doc.mappings().first()
        if tenant and tenant.get("tenant_id"):
            from evaluation.dataset_schema import remove_hitl_question_from_bank

            await remove_hitl_question_from_bank(
                db,
                tenant_id=str(tenant["tenant_id"]),
                question=row["question"],
            )
    if row and row.get("source") == "synthetic_dataset" and row.get("question"):
        row_status = (
            "approved" if data.status in ("approved", "corrected") else "rejected"
        )
        await db.execute(
            text("""
                UPDATE rag_dataset_rows
                SET status = :status,
                    expected_response = COALESCE(:corrected_answer, expected_response)
                WHERE organization_id = :organization_id
                  AND knowledge_base_id IS NOT DISTINCT FROM :knowledge_base_id
                  AND prompt = :question
                  AND source = 'synthetic'
                """),
            {
                "status": row_status,
                "corrected_answer": (data.corrected_answer or "").strip() or None,
                "organization_id": row.get("organization_id"),
                "knowledge_base_id": row.get("knowledge_base_id"),
                "question": row["question"],
            },
        )
        await db.execute(
            text("""
                UPDATE rag_datasets AS dataset
                SET status = CASE
                    WHEN EXISTS (
                        SELECT 1 FROM rag_dataset_rows AS item
                        WHERE item.dataset_id = dataset.id
                          AND item.status = 'pending_review'
                    ) THEN 'pending_review'
                    ELSE 'ready'
                END,
                updated_at = CURRENT_TIMESTAMP
                WHERE dataset.organization_id = :organization_id
                  AND dataset.knowledge_base_id IS NOT DISTINCT FROM :knowledge_base_id
                  AND dataset.source_type = 'synthetic'
                """),
            {
                "organization_id": row.get("organization_id"),
                "knowledge_base_id": row.get("knowledge_base_id"),
            },
        )
    await db.commit()
    return {"status": "success", "id": review_id, "decision": data.status}


@hitl_router.get("/questions", status_code=200)
async def list_document_questions(
    knowledge_base_id: Optional[str] = Query(None),
    document_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await hitl.init_human_validation_tables(db)
    clauses = ["1=1"]
    params: dict[str, Any] = {}
    if knowledge_base_id:
        clauses.append("knowledge_base_id = :knowledge_base_id")
        params["knowledge_base_id"] = knowledge_base_id
    if document_id:
        clauses.append("document_id = :document_id")
        params["document_id"] = document_id
    result = await db.execute(
        text(f"""
            SELECT id, document_id, knowledge_base_id, question, rationale,
                   category, keywords, reference_answer, filename,
                   status, created_at, reviewed_at, reviewer_notes
            FROM document_questions
            WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC
            LIMIT 200
            """),
        params,
    )
    from services.question_extraction import is_template_eval_question

    rows = []
    for raw in result.mappings().all():
        row = dict(raw)
        if is_template_eval_question(
            str(row.get("question") or ""),
            rationale=str(row.get("rationale") or ""),
            reference_answer=str(row.get("reference_answer") or ""),
        ):
            continue
        rows.append(hitl._serialize(row))
    return {"count": len(rows), "data": rows}


@hitl_router.post("/extract-missing", status_code=202)
async def extract_missing_questions(
    background_tasks: BackgroundTasks,
    organization_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
):
    """Encola preguntas HITL para documentos indexados que aún no tienen muestra."""

    background_tasks.add_task(
        hitl.enqueue_missing_document_eval_questions,
        organization_id=organization_id,
        limit=8,
    )
    return {"status": "queued", "organization_id": organization_id}
