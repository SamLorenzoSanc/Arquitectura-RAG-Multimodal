from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from services.rag_dataset_service import (
    add_llm_column,
    append_rows,
    delete_dataset,
    enqueue_synthetic_hitl,
    evaluate_row_guardrails,
    infer_mapping,
    init_rag_dataset_tables,
    list_traces,
    normalize_row,
    pair_chat_messages,
    parse_content,
    render_template,
    run_guardrails,
    sanitize_column_name,
    traces_from_rows,
    update_dataset,
)

pytestmark = pytest.mark.unit


def test_csv_preview_infers_rag_mapping():
    rows, info = parse_content(
        "dataset.csv",
        b"question,answer,ground_truth,isla\nComo regar?,Por goteo,Usar goteo,Tenerife\n",
        "text/csv",
    )

    assert rows[0]["question"] == "Como regar?"
    assert info["kind"] == "tabular"
    assert info["columns"] == ["question", "answer", "ground_truth", "isla"]
    assert info["schema_mapping"]["isla"]["columnType"] == "string"
    assert info["suggested_mapping"] == {
        "prompt": "question",
        "response": "answer",
        "expected_response": "ground_truth",
    }


def test_jsonl_and_normalization_are_deterministic():
    content = b'{"query":"Q","contexts":["C"],"answer":"A"}\n'
    rows, info = parse_content("sample.jsonl", content)
    mapping = info["suggested_mapping"]

    first = normalize_row(rows[0], mapping)
    second = normalize_row(rows[0], mapping)

    assert first["prompt"] == "Q"
    assert first["context"] == ["C"]
    assert first["code_hash"] == second["code_hash"]


def test_binary_pdf_preview_does_not_require_utf8(monkeypatch):
    monkeypatch.setattr(
        "services.question_extraction.extract_text",
        lambda *_args, **_kwargs: "Estatuto de la cooperativa agraria\nArtículo 1.",
    )
    binary = b"%PDF-1.4\n" + bytes([0xE2, 0x80, 0x99]) + b"\ntrailer"
    rows, info = parse_content(
        "Estatuto_Cooperativa_Agraria.pdf", binary, "application/pdf"
    )

    assert info["kind"] == "chunks"
    assert rows[0]["headline"].startswith("Estatuto")
    assert "Artículo" in rows[0]["fragment"]


def test_document_preview_exposes_chunks(monkeypatch):
    monkeypatch.setattr(
        "services.question_extraction.extract_text",
        lambda *_args, **_kwargs: (
            "Riego inteligente\nOptimiza el agua de la finca.\n"
            "Aplicación: programación de riegos por parcela."
        ),
    )
    rows, info = parse_content("manual.pdf", b"%PDF", "application/pdf")

    assert info["kind"] == "chunks"
    assert info["columns"] == [
        "chunk_index",
        "headline",
        "summary",
        "fragment",
        "filename",
        "metadata",
    ]
    assert rows[0]["headline"] == "Riego inteligente"
    assert "Optimiza" in rows[0]["fragment"]
    assert info["suggested_mapping"] == {
        "prompt": "headline",
        "context": "fragment",
        "expected_response": "summary",
        "metadata": "metadata",
    }
    assert info["chunks"][0]["chunk_index"] == 0


def test_invalid_json_is_422():
    with pytest.raises(HTTPException) as exc:
        parse_content("bad.json", b"{")
    assert exc.value.status_code == 422


def test_alias_mapping_accepts_spanish_columns():
    assert infer_mapping(["pregunta", "respuesta", "contexto"]) == {
        "prompt": "pregunta",
        "context": "contexto",
        "response": "respuesta",
    }


def test_log_lines_and_demo_catalog_are_importable():
    from services.rag_dataset_service import demo_catalog, demo_rows, parse_content

    rows, info = parse_content(
        "inferencias.log",
        b'{"prompt":"Q","response":"A"}\nlinea suelta\n',
        "text/plain",
    )
    assert rows[0]["prompt"] == "Q"
    assert rows[1]["prompt"] == "linea suelta"
    assert info["suggested_mapping"]["prompt"] == "prompt"
    assert info["kind"] == "tabular"

    catalog = demo_catalog()
    assert {item["id"] for item in catalog} >= {"posei-faq", "riego-gotero"}
    name, _, demo = demo_rows("posei-faq")
    assert "POSEI" in name
    assert demo[0]["prompt"]


def test_excel_extracts_all_columns():
    from io import BytesIO

    openpyxl = pytest.importorskip("openpyxl")

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["pregunta", "isla", "hectareas", "activo"])
    sheet.append(["¿Cómo riego?", "La Palma", 12.5, True])
    buffer = BytesIO()
    workbook.save(buffer)

    rows, info = parse_content(
        "sat.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    assert info["kind"] == "tabular"
    assert info["columns"] == ["pregunta", "isla", "hectareas", "activo"]
    assert rows[0]["isla"] == "La Palma"
    assert info["schema_mapping"]["hectareas"]["columnType"] == "float"
    assert info["suggested_mapping"]["prompt"] == "pregunta"


def test_json_extracts_union_of_all_keys():
    rows, info = parse_content(
        "casos.json",
        b'[{"pregunta":"A","extra":1},{"pregunta":"B","nota":"x","extra":2}]',
        "application/json",
    )
    assert info["columns"] == ["pregunta", "extra", "nota"]
    assert info["kind"] == "tabular"
    assert rows[1]["nota"] == "x"


def test_semicolon_csv_keeps_every_header():
    rows, info = parse_content(
        "export.csv",
        "col_a;col_b;col_c\n1;2;3\n".encode("utf-8"),
        "text/csv",
    )
    assert info["columns"] == ["col_a", "col_b", "col_c"]
    assert rows[0]["col_c"] == "3"


def test_unmapped_columns_are_kept_in_metadata():
    row = normalize_row(
        {"question": "¿Riego?", "isla": "Tenerife", "nota": "gota"},
        {"prompt": "question"},
    )
    assert row["prompt"] == "¿Riego?"
    assert row["metadata"]["source_columns"]["isla"] == "Tenerife"
    assert row["metadata"]["source_columns"]["nota"] == "gota"


def test_video_preview_uses_transcribed_segments(monkeypatch):
    monkeypatch.setattr(
        "services.rag_dataset_service._video_segments",
        lambda *_args, **_kwargs: [
            "[0.0s–2.1s] Revisa el filtro de malla.",
            "[2.1s–5.0s] Sustituye goteros ciegos.",
        ],
    )
    rows, info = parse_content("riego.mp4", b"fake-video", "video/mp4")
    assert info["kind"] == "chunks"
    assert info["format"] == "video"
    assert len(rows) == 2
    assert "filtro" in rows[0]["fragment"]
    assert rows[1]["chunk_index"] == 1


def test_pptx_preview_exposes_slide_fragments(monkeypatch):
    monkeypatch.setattr(
        "services.question_extraction.extract_text",
        lambda *_args, **_kwargs: "Diapositiva 1\nRiego por goteo en platanera.",
    )
    rows, info = parse_content("charla.pptx", b"not-a-zip", "application/vnd.ms-powerpoint")
    assert info["kind"] == "chunks"
    assert "Riego" in rows[0]["fragment"]



@pytest.mark.asyncio
async def test_synthetic_rows_are_queued_for_human_validation():
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=False)
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    queued = await enqueue_synthetic_hitl(
        db,
        rows=[
            {
                "prompt": "¿Qué exige la BCAM 6?",
                "context": ["La BCAM 6 exige cobertura mínima del suelo."],
                "expected_response": "Mantener cobertura mínima.",
                "metadata": {"document_id": "11111111-1111-1111-1111-111111111111"},
            }
        ],
        organization_id="22222222-2222-2222-2222-222222222222",
        knowledge_base_id="33333333-3333-3333-3333-333333333333",
        user_id="44444444-4444-4444-4444-444444444444",
    )

    assert queued == 1
    insert_call = db.execute.await_args
    assert "'synthetic_dataset'" in str(insert_call.args[0])
    assert insert_call.args[1]["question"] == "¿Qué exige la BCAM 6?"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_init_tables_skips_external_sql_when_already_present(monkeypatch):
    import services.rag_dataset_service as module

    monkeypatch.setattr(module, "_TABLES_READY", False)
    db = AsyncMock()
    db.scalar = AsyncMock(return_value="rag_datasets")
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await init_rag_dataset_tables(db)

    db.scalar.assert_awaited_once()
    db.execute.assert_not_awaited()
    db.commit.assert_not_awaited()
    assert module._TABLES_READY is True


@pytest.mark.asyncio
async def test_delete_dataset_removes_ingest_after_scope_check(monkeypatch):
    db = AsyncMock()
    mappings = MagicMock()
    mappings.first.return_value = {
        "id": "ds-1",
        "name": "FAQ",
        "description": None,
        "knowledge_base_id": None,
        "mapping": {},
        "status": "ready",
    }
    result = MagicMock()
    result.mappings.return_value = mappings
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    monkeypatch.setattr(
        "services.rag_dataset_service._notify_index", AsyncMock()
    )

    out = await delete_dataset(
        db,
        dataset_id="ds-1",
        organization_id="org-1",
        tenant_id="tenant-1",
    )

    assert out == {"id": "ds-1", "deleted": True}
    sqls = [str(call.args[0]) for call in db.execute.await_args_list]
    assert any("DELETE FROM rag_datasets" in sql for sql in sqls)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_dataset_writes_name_and_departments(monkeypatch):
    db = AsyncMock()
    mappings = MagicMock()
    mappings.first.return_value = {
        "id": "ds-1",
        "name": "Viejo",
        "description": "antes",
        "knowledge_base_id": None,
        "mapping": {"prompt": "pregunta"},
        "status": "ready",
    }
    result = MagicMock()
    result.mappings.return_value = mappings
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    monkeypatch.setattr(
        "services.rag_dataset_service._notify_index", AsyncMock()
    )
    monkeypatch.setattr(
        "services.rag_dataset_service.associate_dataset_departments",
        AsyncMock(),
    )

    out = await update_dataset(
        db,
        dataset_id="ds-1",
        organization_id="org-1",
        tenant_id="tenant-1",
        user_id="user-1",
        name="Nuevo nombre",
        description="actualizado",
        department_ids=["dept-1"],
    )

    assert out["name"] == "Nuevo nombre"
    assert out["description"] == "actualizado"
    sqls = [str(call.args[0]) for call in db.execute.await_args_list]
    assert any("UPDATE rag_datasets" in sql for sql in sqls)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_append_rows_reuses_existing_schema_mapping(monkeypatch):
    db = AsyncMock()
    mappings = MagicMock()
    mappings.first.return_value = {
        "id": "ds-1",
        "name": "FAQ",
        "description": None,
        "knowledge_base_id": None,
        "mapping": {"prompt": "pregunta", "expected_response": "respuesta"},
        "status": "ready",
        "organization_id": "org-1",
        "tenant_id": "tenant-1",
        "row_count": 1,
        "source_type": "upload",
    }
    result = MagicMock()
    result.mappings.return_value = mappings
    result.rowcount = 1
    db.execute = AsyncMock(return_value=result)
    db.scalar = AsyncMock(return_value=2)
    db.commit = AsyncMock()
    monkeypatch.setattr("services.rag_dataset_service._notify_index", AsyncMock())

    out = await append_rows(
        db,
        dataset_id="ds-1",
        rows=[{"pregunta": "¿Riego?", "respuesta": "Por goteo"}],
        organization_id="org-1",
        tenant_id="tenant-1",
        source_name="extra.csv",
    )

    assert out["imported_rows"] == 1
    assert out["row_count"] == 2
    sqls = [str(call.args[0]) for call in db.execute.await_args_list]
    assert any("INSERT INTO rag_dataset_rows" in sql for sql in sqls)


def test_render_template_and_column_name():
    text = render_template(
        "P: {{prompt}} C: {{context}}",
        {"prompt": "¿Riego?", "context": "Goteo", "response": ""},
    )
    assert text == "P: ¿Riego? C: Goteo"
    assert sanitize_column_name("Veredicto LLM") == "Veredicto_LLM"


def test_pair_chat_messages_and_traces_from_rows():
    pairs = pair_chat_messages(
        [
            {
                "id": "1",
                "role": "user",
                "content": "¿Cómo riego?",
                "conversation_id": "c1",
            },
            {
                "id": "2",
                "role": "assistant",
                "content": "Por goteo",
                "conversation_id": "c1",
            },
        ]
    )
    assert len(pairs) == 1
    assert pairs[0]["prompt"] == "¿Cómo riego?"
    assert pairs[0]["traceId"] == "2"

    traces = traces_from_rows(
        [
            {
                "id": "r1",
                "traceId": "2",
                "prompt": "¿Cómo riego?",
                "context": ["Manual de riego"],
                "response": "Por goteo",
                "metadata": {"guardrails": {"passed": True, "flags": []}},
            }
        ]
    )
    assert traces[0]["spans"][0]["name"] == "user"
    assert traces[0]["guardrails"]["passed"] is True


def test_evaluate_row_guardrails_flags_hallucination_and_pii():
    flagged = evaluate_row_guardrails(
        {
            "prompt": "¿Cuántas hectáreas? Contacto finca@agrops.es",
            "context": ["La finca tiene olivos en Tenerife"],
            "response": "Hay 120 hectáreas de riego",
        }
    )
    assert flagged["passed"] is False
    assert "hallucination" in flagged["flags"]
    assert "pii" in flagged["flags"]

    grounded = evaluate_row_guardrails(
        {
            "prompt": "¿Riego?",
            "context": ["Se riega por goteo"],
            "response": "Se riega por goteo",
        }
    )
    assert grounded["passed"] is True
    assert grounded["flags"] == []


def _dataset_scope():
    return {
        "id": "ds-1",
        "name": "FAQ",
        "description": None,
        "knowledge_base_id": None,
        "mapping": {"prompt": "prompt", "response": "response"},
        "status": "ready",
        "organization_id": "org-1",
        "tenant_id": "tenant-1",
        "row_count": 1,
        "source_type": "upload",
    }


def _execute_mock(dataset, rows=None, messages=None, count=1):
    rows = rows or []
    messages = messages or []

    async def execute(query, params=None):
        sql = str(query)
        result = MagicMock()
        result.rowcount = 1
        mappings = MagicMock()
        if "FROM rag_datasets" in sql:
            mappings.first.return_value = dataset
        elif "FROM messages" in sql:
            mappings.all.return_value = messages
        elif "FROM rag_dataset_rows" in sql:
            mappings.all.return_value = rows
        result.mappings.return_value = mappings
        return result

    return execute


@pytest.mark.asyncio
async def test_add_llm_column_writes_metadata(monkeypatch):
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=_execute_mock(
            _dataset_scope(),
            rows=[
                {
                    "id": "r1",
                    "prompt": "¿Riego?",
                    "context": ["Goteo"],
                    "response": "Por goteo",
                    "metadata": {},
                }
            ],
        )
    )
    db.commit = AsyncMock()

    async def fake_complete(prompt: str) -> str:
        assert "¿Riego?" in prompt
        return "Fundado en el contexto"

    out = await add_llm_column(
        db,
        dataset_id="ds-1",
        organization_id="org-1",
        tenant_id="tenant-1",
        column_name="veredicto",
        prompt_template="{{prompt}} | {{response}}",
        completer=fake_complete,
    )
    assert out["filled_rows"] == 1
    assert out["column_name"] == "veredicto"
    sqls = [str(call.args[0]) for call in db.execute.await_args_list]
    assert any("UPDATE rag_dataset_rows" in sql for sql in sqls)
    payload = db.execute.await_args_list[-1].args[1]
    assert "Fundado en el contexto" in payload["metadata"]


@pytest.mark.asyncio
async def test_run_guardrails_persists_flags():
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=_execute_mock(
            _dataset_scope(),
            rows=[
                {
                    "id": "r1",
                    "traceId": "t1",
                    "prompt": "¿Hectáreas?",
                    "context": ["Olivos en Tenerife"],
                    "response": "Hay 90 hectáreas",
                    "metadata": {},
                }
            ],
        )
    )
    db.commit = AsyncMock()

    out = await run_guardrails(
        db,
        dataset_id="ds-1",
        organization_id="org-1",
        tenant_id="tenant-1",
    )
    assert out["scanned"] == 1
    assert out["flagged"] == 1
    assert out["flags"]["hallucination"] == 1


@pytest.mark.asyncio
async def test_list_traces_builds_spans():
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=_execute_mock(
            _dataset_scope(),
            rows=[
                {
                    "id": "r1",
                    "traceId": "abc",
                    "prompt": "Q",
                    "context": ["C"],
                    "response": "A",
                    "metadata": {},
                }
            ],
        )
    )

    out = await list_traces(
        db,
        dataset_id="ds-1",
        organization_id="org-1",
        tenant_id="tenant-1",
    )
    assert out["count"] == 1
    assert out["data"][0]["traceId"] == "abc"
    assert [span["name"] for span in out["data"][0]["spans"]] == [
        "user",
        "retrieve",
        "generate",
    ]
