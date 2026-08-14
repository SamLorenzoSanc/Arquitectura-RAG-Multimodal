from __future__ import annotations

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
from services.human_validation import init_human_validation_tables
from services import rag_dataset_service as service

router = APIRouter(prefix="/datasets", tags=["RAG datasets"])


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


@router.get("")
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


@router.post("/preview")
async def preview_dataset(
    file: UploadFile = File(...),
    limit: int = Form(20),
    context: dict = Depends(get_tenant_context),
):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit debe estar entre 1 y 100")
    return await service.preview_upload(file, limit)


@router.post("/import")
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


@router.post("/synthetic")
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


@router.post("/synthetic/preview")
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


@router.get("/demo-catalog")
async def list_demo_datasets(
    _context: dict = Depends(get_tenant_context),
):
    return {"count": len(service.demo_catalog()), "data": service.demo_catalog()}


@router.post("/demo")
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


@router.get("/knowledge-bases/{knowledge_base_id}/departments")
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


@router.put("/knowledge-bases/{knowledge_base_id}/departments")
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


@router.get("/departments/{department_id}/knowledge-bases")
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


@router.get("/{dataset_id}")
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


@router.post("/{dataset_id}/rows")
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


@router.get("/{dataset_id}/traces")
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


@router.post("/{dataset_id}/traces/import")
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


@router.post("/{dataset_id}/columns")
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


@router.post("/{dataset_id}/guardrails")
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


@router.patch("/{dataset_id}")
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


@router.delete("/{dataset_id}")
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
