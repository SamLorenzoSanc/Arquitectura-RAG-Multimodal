from unittest.mock import AsyncMock, MagicMock, patch

from schemas.evaluation import DatasetEvaluationRequest
from services.rag_service import RetrievalEval

EXPERIMENTS_ROUTE = "/api/v1/chat/evaluation/experiments"
COMPARE_ROUTE = "/api/v1/chat/evaluation/experiments/compare"
STRATEGIES_ROUTE = "/api/v1/chat/evaluation/experiments/strategies"
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
        "chat.http.get_user_tenant_id", AsyncMock(return_value="tenant-1")
    ), patch("chat.http.init_experiment_runs_table", AsyncMock()):
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
        "chat.http.get_user_tenant_id", AsyncMock(return_value="tenant-1")
    ), patch(
        "chat.http.resolve_evaluation_tests", AsyncMock(return_value=sample)
    ), patch(
        "chat.http.evaluate_retrieval_internal",
        AsyncMock(return_value=_fake_eval()),
    ), patch(
        "chat.http.record_experiment_run", AsyncMock(return_value=saved)
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
        "chat.http.get_user_tenant_id", AsyncMock(return_value="tenant-1")
    ), patch(
        "chat.http.resolve_evaluation_tests", AsyncMock(return_value=sample)
    ), patch(
        "chat.http.evaluate_retrieval_internal",
        AsyncMock(return_value=_fake_eval(mrr=0.9)),
    ), patch(
        "chat.http.record_experiment_run", AsyncMock(return_value=saved)
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
        "chat.http.get_user_tenant_id", AsyncMock(return_value="tenant-1")
    ), patch(
        "chat.http.resolve_evaluation_tests", AsyncMock(return_value=sample)
    ), patch(
        "chat.http.evaluate_retrieval_internal",
        AsyncMock(return_value=_fake_eval(mrr=0.85)),
    ), patch(
        "chat.http.record_experiment_run", AsyncMock(return_value=saved)
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


def test_compare_retrieval_strategies_runs_same_bank(authenticated_client):
    sample = [
        type(
            "T",
            (),
            {
                "question": "¿Qué regula la Orden APA/102/2024?",
                "keywords": ["APA/102/2024"],
                "reference_answer": "Una ayuda agraria.",
                "category": "identifier",
                "out_of_knowledge": False,
                "metadata": {},
            },
        )()
    ]
    evaluator = AsyncMock(return_value=_fake_eval(mrr=0.75))

    with patch(
        "chat.http.get_user_tenant_id", AsyncMock(return_value="tenant-1")
    ), patch(
        "chat.http.resolve_evaluation_tests", AsyncMock(return_value=sample)
    ), patch(
        "chat.http.evaluate_retrieval_internal", evaluator
    ), patch(
        "chat.http.record_experiment_run",
        AsyncMock(side_effect=[
            {"id": 21, "created_at": None},
            {"id": 22, "created_at": None},
        ]),
    ) as persist:
        res = authenticated_client.post(
            STRATEGIES_ROUTE,
            json={
                "strategies": ["dense", "hybrid_rrf"],
                "embedding_model": "qwen3-embedding:latest",
                "distance_metric": "cosine",
                "top_k": 5,
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert len(body["runs"]) == 2
    assert persist.await_count == 2
    assert {run["retrieval_strategy"] for run in body["runs"]} == {
        "dense",
        "hybrid_rrf",
    }
    assert {
        call.kwargs["retrieval_strategy"] for call in evaluator.await_args_list
    } == {"dense", "hybrid_rrf"}


def test_dataset_evaluation_request_can_skip_cache():
    assert DatasetEvaluationRequest().force is False
    assert DatasetEvaluationRequest(force=True).force is True


INDEXED_MODELS_ROUTE = "/api/v1/chat/evaluation/experiments/indexed-models"


def test_indexed_models_runs_each_embedding(authenticated_client):
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
    persist = AsyncMock(
        side_effect=[
            {"id": 31, "created_at": None},
            {"id": 32, "created_at": None},
        ]
    )

    with patch(
        "chat.http.get_user_tenant_id",
        AsyncMock(return_value="tenant-1"),
    ), patch(
        "chat.http.resolve_evaluation_tests",
        AsyncMock(return_value=sample),
    ), patch(
        "chat.http.evaluate_retrieval_internal",
        AsyncMock(return_value=_fake_eval(mrr=0.7)),
    ), patch(
        "chat.http.record_experiment_run", persist
    ):
        res = authenticated_client.post(
            INDEXED_MODELS_ROUTE,
            json={
                "distance_metric": "cosine",
                "top_k": 3,
                "embedding_models": [
                    "nomic-embed-text",
                    "qwen3-embedding:latest",
                ],
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert len(body["runs"]) == 2
    assert persist.await_count == 2
    assert {run["embedding_model"] for run in body["runs"]} == {
        "nomic-embed-text",
        "qwen3-embedding:latest",
    }
    assert {run["experiment_type"] for run in body["runs"]} == {"question_bank"}
    assert body["best_mrr_id"] in {31, 32}


def test_indexed_models_discovers_from_index(authenticated_client):
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

    with patch(
        "chat.http.get_user_tenant_id",
        AsyncMock(return_value="tenant-1"),
    ), patch(
        "chat.http.resolve_evaluation_tests",
        AsyncMock(return_value=sample),
    ), patch(
        "chat.http._indexed_embedding_models",
        AsyncMock(return_value=["mxbai-embed-large", "nomic-embed-text"]),
    ), patch(
        "chat.http.evaluate_retrieval_internal",
        AsyncMock(return_value=_fake_eval(mrr=0.6)),
    ), patch(
        "chat.http.record_experiment_run",
        AsyncMock(
            side_effect=[
                {"id": 41, "created_at": None},
                {"id": 42, "created_at": None},
            ]
        ),
    ) as persist:
        res = authenticated_client.post(
            INDEXED_MODELS_ROUTE,
            json={"distance_metric": "cosine", "persist": True},
        )

    assert res.status_code == 200
    body = res.json()
    assert len(body["runs"]) == 2
    assert persist.await_count == 2
    assert [run["embedding_model"] for run in body["runs"]] == [
        "mxbai-embed-large",
        "nomic-embed-text",
    ]
