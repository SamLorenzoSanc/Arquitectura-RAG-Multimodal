import json
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

GET_TESTS_ROUTE = "/chat/evaluation/tests"
GET_TEST_ROUTE = "/chat/evaluation/tests/0"
EVAL_RETRIEVAL_ROUTE = "/chat/evaluation/retrieval/0"
EVAL_ANSWER_ROUTE = "/chat/evaluation/answer/0"
UPLOAD_TESTS_ROUTE = "/chat/evaluation/upload-tests"


def make_test_question():
    return SimpleNamespace(
        question="¿Cuál es la capital de España?",
        keywords=["España", "capital"],
        reference_answer="Madrid",
        category="geografía",
    )


def test_get_evaluation_tests(authenticated_client):
    sample = [make_test_question()]

    with patch("routes.chat.load_tests", return_value=sample):
        res = authenticated_client.get(GET_TESTS_ROUTE)

    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["tests"][0]["question"] == sample[0].question


def test_get_evaluation_test_not_found(authenticated_client):
    sample = [make_test_question()]

    with patch("routes.chat.load_tests", return_value=sample):
        res = authenticated_client.get("/chat/evaluation/tests/99")

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

    with patch("routes.chat.load_tests", return_value=sample), patch(
        "routes.chat.get_user_tenant_id", AsyncMock(return_value="tenant-1")
    ), patch("routes.chat.evaluate_retrieval_internal", async_mock):
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

    async_mock = AsyncMock(return_value=(eval_result, generated_answer, chunks))

    with patch("routes.chat.load_tests", return_value=sample), patch(
        "routes.chat.get_user_tenant_id", AsyncMock(return_value="tenant-1")
    ), patch("routes.chat.evaluate_answer_internal", async_mock):
        res = authenticated_client.post(EVAL_ANSWER_ROUTE)

    assert res.status_code == 200
    body = res.json()
    assert body["evaluation"]["accuracy"] == 5.0


def test_upload_tests_endpoint(authenticated_client, tmp_path):
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
    with patch("routes.chat.TEST_FILE", destination), open(file_path, "rb") as fh:
        files = {"file": ("tests.json", fh, "application/json")}
        res = authenticated_client.post(UPLOAD_TESTS_ROUTE, files=files)

    assert res.status_code == 200
    body = res.json()
    assert body.get("uploaded", 0) >= 1
