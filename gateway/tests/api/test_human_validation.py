"""Tests de extracción de preguntas y validación humana."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.human_validation import save_document_questions
from services.question_extraction import (
    EVAL_CATEGORIES,
    _parse_llm_questions,
    heuristic_questions,
)

pytestmark = pytest.mark.api


def test_heuristic_questions_from_text():
    text = "¿Cuál es la dosis de riego? El resto es prosa. ¿Qué hacer ante trips?"
    out = heuristic_questions(text, "manual_platano.pdf")
    assert any("dosis" in q["question"].lower() for q in out)
    assert all(q["category"] in EVAL_CATEGORIES for q in out)
    assert len(out) >= 2


def test_parse_llm_questions_json():
    raw = '{"questions": [{"question": "¿Cómo podo?", "category": "direct_fact", "rationale": "manejo"}]}'
    parsed = _parse_llm_questions(raw)
    assert parsed[0]["question"] == "¿Cómo podo?"
    assert parsed[0]["category"] == "direct_fact"


def test_categorize_question_domain():
    from services.question_extraction import categorize_question

    assert categorize_question("¿Qué exige la BCAM 6?") == "regulatory_compliance"
    assert categorize_question("¿Qué temperatura lleva el reefer?") == "direct_fact"
    assert (
        categorize_question("¿En qué página y anexo se detallan los criterios?")
        == "traceability"
    )
    assert (
        categorize_question("¿Desde qué año ocupa el puesto de director?") == "temporal"
    )


def test_llm_categories_are_restricted_to_requested_taxonomy():
    raw = """
    {"questions": [
      {"question": "¿Qué temperatura lleva el reefer?", "category": "cadena_frio"},
      {"question": "¿Qué plazo debe cumplir?", "category": "temporal"}
    ]}
    """
    parsed = _parse_llm_questions(raw)
    assert {item["category"] for item in parsed} <= set(EVAL_CATEGORIES)
    assert parsed[0]["category"] == "direct_fact"


def test_list_reviews_requires_auth(client):
    response = client.get("/api/v1/human-validation/reviews")
    assert response.status_code in (401, 403, 422)


def test_list_reviews(authenticated_client, override_db):
    result = MagicMock()
    result.mappings.return_value.all.return_value = [
        {
            "id": "r1",
            "source": "chat",
            "user_id": "user-123",
            "organization_id": None,
            "conversation_id": None,
            "document_id": None,
            "question": "¿Riego?",
            "answer": "Goteo",
            "context_snippet": None,
            "chunk_ids": [],
            "status": "pending",
            "corrected_answer": None,
            "reviewer_notes": None,
            "reviewer_id": None,
            "created_at": None,
            "reviewed_at": None,
        }
    ]
    override_db.execute = AsyncMock(return_value=result)
    override_db.commit = AsyncMock()
    with patch("routes.human_validation.init_human_validation_tables", new=AsyncMock()):
        response = authenticated_client.get("/api/v1/human-validation/reviews")
    assert response.status_code == 200
    assert response.json()["data"][0]["question"] == "¿Riego?"


def test_list_reviews_defaults_to_document_questions(authenticated_client, override_db):
    result = MagicMock()
    result.mappings.return_value.all.return_value = []
    override_db.execute = AsyncMock(return_value=result)
    override_db.commit = AsyncMock()
    with patch("routes.human_validation.init_human_validation_tables", new=AsyncMock()):
        response = authenticated_client.get("/api/v1/human-validation/reviews")
    assert response.status_code == 200
    params = override_db.execute.await_args.args[1]
    assert params["source"] == "document_question"


def test_decide_review(authenticated_client, override_db):
    update = MagicMock()
    update.rowcount = 1
    select = MagicMock()
    select.mappings.return_value.first.return_value = {
        "document_id": None,
        "question": "¿Riego?",
    }
    override_db.execute = AsyncMock(side_effect=[update, select])
    override_db.commit = AsyncMock()
    with patch("routes.human_validation.init_human_validation_tables", new=AsyncMock()):
        response = authenticated_client.post(
            "/api/v1/human-validation/reviews/r1",
            json={"status": "approved", "reviewer_notes": "Correcto"},
        )
    assert response.status_code == 200
    assert response.json()["decision"] == "approved"


def test_decide_review_promotes_approved_document_question(
    authenticated_client, override_db
):
    update = MagicMock()
    update.rowcount = 1
    select = MagicMock()
    select.mappings.return_value.first.return_value = {
        "document_id": "doc-1",
        "question": "¿Qué es una SAT?",
        "source": "document_question",
        "answer": "Sociedad Agraria de Transformación.",
        "category": "sat",
        "filename": "sat.pdf",
    }
    question_update = MagicMock()
    override_db.execute = AsyncMock(side_effect=[update, select, question_update])
    override_db.commit = AsyncMock()
    with (
        patch("routes.human_validation.init_human_validation_tables", new=AsyncMock()),
        patch(
            "routes.human_validation.promote_review_to_evaluation_bank",
            new=AsyncMock(),
        ) as promote,
    ):
        response = authenticated_client.post(
            "/api/v1/human-validation/reviews/r1",
            json={"status": "approved", "reviewer_notes": "Correcto"},
        )
    assert response.status_code == 200
    promote.assert_awaited_once()


def test_decide_synthetic_review_updates_dataset_row(authenticated_client, override_db):
    update = MagicMock()
    update.rowcount = 1
    select = MagicMock()
    select.mappings.return_value.first.return_value = {
        "document_id": None,
        "question": "¿Qué producción tuvo la finca?",
        "source": "synthetic_dataset",
        "answer": "20 toneladas",
        "organization_id": "org-1",
        "knowledge_base_id": "kb-1",
    }
    override_db.execute = AsyncMock(
        side_effect=[update, select, MagicMock(), MagicMock()]
    )
    override_db.commit = AsyncMock()
    with patch("routes.human_validation.init_human_validation_tables", new=AsyncMock()):
        response = authenticated_client.post(
            "/api/v1/human-validation/reviews/r1",
            json={"status": "corrected", "corrected_answer": "21 toneladas"},
        )
    assert response.status_code == 200
    sqls = " ".join(
        str(call.args[0]) for call in override_db.execute.await_args_list[2:]
    )
    assert "rag_dataset_rows" in sqls
    assert "rag_datasets" in sqls


@pytest.mark.asyncio
async def test_save_document_questions_enqueues_human_reviews():
    db = AsyncMock()
    stored = await save_document_questions(
        db,
        document_id="doc-1",
        knowledge_base_id="kb-1",
        organization_id="org-1",
        user_id="user-1",
        questions=[
            {
                "question": "¿Qué es una SAT?",
                "category": "sat",
                "rationale": "definición del documento",
                "keywords": ["SAT"],
                "reference_answer": "Sociedad Agraria de Transformación.",
            }
        ],
        filename="sat.pdf",
    )
    assert len(stored) == 1
    assert stored[0]["status"] == "pending"
    assert stored[0]["filename"] == "sat.pdf"
    sqls = " ".join(str(call.args[0]) for call in db.execute.await_args_list)
    assert "document_questions" in sqls
    assert "rag_human_reviews" in sqls
    review_params = db.execute.await_args_list[1].args[1]
    assert review_params["answer"] == "Sociedad Agraria de Transformación."
    db.commit.assert_awaited()
