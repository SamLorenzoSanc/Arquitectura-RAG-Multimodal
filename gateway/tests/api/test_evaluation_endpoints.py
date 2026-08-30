import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.test import TestQuestion

GET_TESTS_ROUTE = "/api/v1/chat/evaluation/tests"
GET_TEST_ROUTE = "/api/v1/chat/evaluation/tests/0"
EVAL_RETRIEVAL_ROUTE = "/api/v1/chat/evaluation/retrieval/0"
EVAL_ANSWER_ROUTE = "/api/v1/chat/evaluation/answer/0"
UPLOAD_TESTS_ROUTE = "/api/v1/chat/evaluation/upload-tests"


def make_test_question():
    return TestQuestion(
        question="¿Cuál es la capital de España?",
        keywords=["España", "capital"],
        reference_answer="Madrid",
        category="geografía",
        source_file="knowledge-base/asesor-canarias/02_posei_marco.md",
        page="marco",
    )


def test_get_evaluation_tests(authenticated_client):
    sample = [make_test_question()]

    with patch(
        "chat.http.resolve_evaluation_tests", AsyncMock(return_value=sample)
    ):
        res = authenticated_client.get(GET_TESTS_ROUTE)

    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["tests"][0]["question"] == sample[0].question
    assert body["tests"][0]["source"] == "file"
    assert body["tests"][0]["source_file"].endswith("02_posei_marco.md")
    assert body["tests"][0]["page"] == "marco"


def test_get_evaluation_test_not_found(authenticated_client):
    sample = [make_test_question()]

    with patch(
        "chat.http.resolve_evaluation_tests", AsyncMock(return_value=sample)
    ):
        res = authenticated_client.get("/api/v1/chat/evaluation/tests/99")

    assert res.status_code == 404


@pytest.mark.asyncio
async def test_evaluate_retrieval_route(authenticated_client):
    sample = [make_test_question()]

    fake_result = {
        "mrr": 1.0,
        "ndcg": 1.0,
        "keyword_coverage": 100.0,
    }

    async_mock = AsyncMock(return_value=fake_result)

    with patch(
        "chat.http.resolve_evaluation_tests", AsyncMock(return_value=sample)
    ), patch(
        "chat.http.get_user_tenant_id", AsyncMock(return_value="tenant-1")
    ), patch("chat.http.evaluate_retrieval_internal", async_mock):
        res = authenticated_client.post(EVAL_RETRIEVAL_ROUTE)

    assert res.status_code == 200
    body = res.json()
    assert body["retrieval"]["mrr"] == 1.0


@pytest.mark.asyncio
async def test_evaluate_answer_route(authenticated_client):
    sample = [make_test_question()]

    eval_result = {"accuracy": 5.0, "completeness": 5.0, "relevance": 5.0}
    generated_answer = "Madrid"
    chunks = []
    retrieval = {"mrr": 1.0, "ndcg": 1.0, "keyword_coverage": 100.0}

    vanilla_eval = {"accuracy": 2.0, "completeness": 2.0, "relevance": 2.0}
    vanilla_answer = "No lo sé"
    ragas_bundle = {
        "ragas": {
            "faithfulness": 0.9,
            "answer_relevancy": 0.85,
            "context_precision": 0.8,
            "context_recall": 0.75,
        },
        "vanilla_ragas": {
            "faithfulness": 0.2,
            "answer_relevancy": 0.4,
            "context_precision": 0.0,
            "context_recall": 0.0,
        },
        "ragas_source": "ragas",
        "is_hallucination": False,
        "vanilla_is_hallucination": True,
    }
    async_mock = AsyncMock(
        return_value=(
            eval_result,
            generated_answer,
            chunks,
            retrieval,
            vanilla_eval,
            vanilla_answer,
            ragas_bundle,
        )
    )

    with patch(
        "chat.http.resolve_evaluation_tests", AsyncMock(return_value=sample)
    ), patch(
        "chat.http.get_user_tenant_id", AsyncMock(return_value="tenant-1")
    ), patch("chat.http.evaluate_answer_internal", async_mock):
        res = authenticated_client.post(EVAL_ANSWER_ROUTE)

    assert res.status_code == 200
    body = res.json()
    assert body["evaluation"]["accuracy"] == 5.0
    assert body["retrieval"]["mrr"] == 1.0
    assert body["vanilla_evaluation"]["accuracy"] == 2.0
    assert body["vanilla_answer"] == "No lo sé"
    assert body["comparison_mode"] == "no_rag_vs_rag"
    assert body["ragas"]["faithfulness"] == 0.9
    assert body["vanilla_ragas"]["faithfulness"] == 0.2
    assert body["ragas_source"] == "ragas"


def test_upload_tests_endpoint(authenticated_client, override_db, tmp_path):
    payload = [
        {
            "question": "¿Cuál es la capital de Francia?",
            "keywords": ["Francia", "capital"],
            "reference_answer": "París",
            "category": "geografía",
        }
    ]

    content = json.dumps(payload, ensure_ascii=False)
    file_path = tmp_path / "tests.json"
    file_path.write_text(content, encoding="utf-8")

    destination = tmp_path / "canonical.jsonl"
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = None
    override_db.execute = AsyncMock(return_value=select_result)
    override_db.commit = AsyncMock()

    with patch("chat.http.TEST_FILE", destination), patch(
        "chat.http.get_user_tenant_id", AsyncMock(return_value="tenant-1")
    ), patch(
        "chat.http.init_retrieval_dataset_table", AsyncMock()
    ), open(file_path, "rb") as fh:
        files = {"file": ("tests.json", fh, "application/json")}
        res = authenticated_client.post(UPLOAD_TESTS_ROUTE, files=files)

    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("uploaded", 0) >= 1
    assert "imported" in body


@pytest.mark.asyncio
async def test_load_unified_tests_rollbacks_after_db_error():
    from chat.http import load_unified_tests

    sample = [make_test_question()]
    db = AsyncMock()
    db.rollback = AsyncMock()
    db.commit = AsyncMock()

    with patch("chat.http.load_tests", return_value=sample), patch(
        "chat.http.init_retrieval_dataset_table",
        AsyncMock(side_effect=RuntimeError("column split does not exist")),
    ):
        tests = await load_unified_tests(db, "11111111-1111-1111-1111-111111111111")

    db.rollback.assert_awaited()
    assert tests[0].question == sample[0].question
    assert db.execute.await_count == 0


@pytest.mark.asyncio
async def test_load_unified_tests_merges_gold_jsonl_with_db_rows():
    from chat.http import load_unified_tests

    gold = [make_test_question()]
    extra = {
        "question": "¿Qué es la Medida II del POSEI?",
        "keywords": ["plátano"],
        "reference_answer": "Ayuda al plátano IGP.",
        "category": "direct_fact",
        "split": "dev",
        "flag_out_of_knowledge": False,
        "flag_different_info": False,
        "selected_chunk_ids": [],
        "expected_chunk_id": "",
        "metadata": {"source": "annotated"},
    }
    db = AsyncMock()
    db.rollback = AsyncMock()
    mappings = MagicMock()
    mappings.all.return_value = [extra]
    result = MagicMock()
    result.mappings.return_value = mappings
    db.execute = AsyncMock(return_value=result)

    with patch("chat.http.load_tests", return_value=gold), patch(
        "chat.http.init_retrieval_dataset_table",
        AsyncMock(),
    ):
        tests = await load_unified_tests(db, "11111111-1111-1111-1111-111111111111")

    assert [item.question for item in tests] == [
        gold[0].question,
        extra["question"],
    ]
