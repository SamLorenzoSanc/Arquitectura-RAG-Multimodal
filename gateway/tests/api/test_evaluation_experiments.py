from unittest.mock import AsyncMock, MagicMock, patch

from schemas.evaluation import DatasetEvaluationRequest
from services.rag_service import RetrievalEval

EXPERIMENTS_ROUTE = "/api/v1/chat/evaluation/experiments"
COMPARE_ROUTE = "/api/v1/chat/evaluation/experiments/compare"
MODELS_ROUTE = "/api/v1/chat/evaluation/embedding-models"


def _fake_eval(**overrides):
    payload = {
        "mrr": 0.8,
        "ndcg": 0.7,
        "keywords_found": 2,
        "total_keywords": 3,
        "keyword_coverage": 66.0,
        "accuracy": 50.0,
    }
    payload.update(overrides)
    return RetrievalEval(**payload)


def test_list_embedding_models(authenticated_client, override_db):
    mock_result = MagicMock()
    mock_result.all.return_value = [("qwen3-embedding:latest",)]
    override_db.execute = AsyncMock(return_value=mock_result)

    res = authenticated_client.get(MODELS_ROUTE)

    assert res.status_code == 200
    body = res.json()
    assert body["indexed"] == ["qwen3-embedding:latest"]
    assert "reindexar" in body["note"].lower()


def test_list_experiments_returns_history(authenticated_client, override_db):
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [
        {
            "id": 7,
            "created_at": None,
            "generation_model": "llama3.2:latest",
            "embedding_model": "qwen3-embedding:latest",
            "distance_metric": "cosine",
            "dataset_size": 12,
            "recall_1": 0.4,
            "recall_k": 0.8,
            "precision_at_k": 0.5,
            "ndcg": 0.61,
            "mrr": 0.72,
            "keyword_coverage": 0.8,
            "accuracy": 0.55,
            "failures": 0,
            "duration_ms": 1200,
            "status": "completed",
            "experiment_type": "distance_compare",
            "parameters": {"top_k": 10, "distance_metric": "cosine"},
        }
    ]
    override_db.execute = AsyncMock(return_value=mock_result)

    with patch(
        "routes.chat.get_user_tenant_id", AsyncMock(return_value="tenant-1")
    ), patch("routes.chat.init_experiment_runs_table", AsyncMock()):
        res = authenticated_client.get(EXPERIMENTS_ROUTE)

    assert res.status_code == 200
    body = res.json()
    assert body[0]["embedding_model"] == "qwen3-embedding:latest"
    assert body[0]["distance_metric"] == "cosine"
    assert body[0]["mrr"] == 0.72


def test_create_experiment_persists_run(authenticated_client, override_db):
    sample = [
        type(
            "T",
            (),
            {
                "question": "¿Qué es SIGPAC?",
                "keywords": ["SIGPAC"],
                "reference_answer": "Identifica parcelas.",
                "category": "direct_fact",
                "out_of_knowledge": False,
                "metadata": {},
            },
        )()
    ]
    saved = {"id": 11, "created_at": None}

    with patch(
        "routes.chat.get_user_tenant_id", AsyncMock(return_value="tenant-1")
    ), patch(
        "routes.chat.resolve_evaluation_tests", AsyncMock(return_value=sample)
    ), patch(
        "routes.chat.evaluate_retrieval_internal",
        AsyncMock(return_value=_fake_eval()),
    ), patch(
        "routes.chat.record_experiment_run", AsyncMock(return_value=saved)
    ):
        res = authenticated_client.post(
            EXPERIMENTS_ROUTE,
            json={
                "embedding_model": "qwen3-embedding:latest",
                "distance_metric": "manhattan",
                "top_k": 5,
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert body["id"] == 11
    assert body["distance_metric"] == "manhattan"
    assert body["experiment_type"] == "question_bank"


def test_compare_experiments_runs_three_distances(authenticated_client):
    sample = [
        type(
            "T",
            (),
            {
                "question": "¿Qué es una SAT?",
                "keywords": ["SAT"],
                "reference_answer": "Sociedad agraria.",
                "category": "direct_fact",
                "out_of_knowledge": False,
                "metadata": {},
            },
        )()
    ]
    saved = {"id": 1, "created_at": None}

    with patch(
        "routes.chat.get_user_tenant_id", AsyncMock(return_value="tenant-1")
    ), patch(
        "routes.chat.resolve_evaluation_tests", AsyncMock(return_value=sample)
    ), patch(
        "routes.chat.evaluate_retrieval_internal",
        AsyncMock(return_value=_fake_eval(mrr=0.9)),
    ), patch(
        "routes.chat.record_experiment_run", AsyncMock(return_value=saved)
    ) as persist:
        res = authenticated_client.post(
            COMPARE_ROUTE,
            json={
                "embedding_models": ["qwen3-embedding:latest"],
                "distance_metrics": ["cosine", "euclidean", "manhattan"],
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert len(body["runs"]) == 3
    assert persist.await_count == 3
    assert {run["distance_metric"] for run in body["runs"]} == {
        "cosine",
        "euclidean",
        "manhattan",
    }


def test_compare_experiments_runs_two_embeddings(authenticated_client):
    sample = [
        type(
            "T",
            (),
            {
                "question": "¿Qué es SIGPAC?",
                "keywords": ["SIGPAC"],
                "reference_answer": "Parcelas.",
                "category": "direct_fact",
                "out_of_knowledge": False,
                "metadata": {},
            },
        )()
    ]
    saved = {"id": 3, "created_at": None}

    with patch(
        "routes.chat.get_user_tenant_id", AsyncMock(return_value="tenant-1")
    ), patch(
        "routes.chat.resolve_evaluation_tests", AsyncMock(return_value=sample)
    ), patch(
        "routes.chat.evaluate_retrieval_internal",
        AsyncMock(return_value=_fake_eval(mrr=0.85)),
    ), patch(
        "routes.chat.record_experiment_run", AsyncMock(return_value=saved)
    ) as persist:
        res = authenticated_client.post(
            COMPARE_ROUTE,
            json={
                "embedding_models": [
                    "qwen3-embedding:latest",
                    "nomic-embed-text",
                ],
                "distance_metrics": ["cosine"],
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert len(body["runs"]) == 2
    assert persist.await_count == 2
    assert {run["embedding_model"] for run in body["runs"]} == {
        "qwen3-embedding:latest",
        "nomic-embed-text",
    }


def test_dataset_evaluation_request_can_skip_cache():
    assert DatasetEvaluationRequest().force is False
    assert DatasetEvaluationRequest(force=True).force is True
