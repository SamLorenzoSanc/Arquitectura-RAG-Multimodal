import json

import pytest

from core.test import load_tests, merge_test_banks, TestQuestion, upsert_test_question_jsonl
from schemas.evaluation import SimulatorSaveRequest
from services.evaluation_dataset import CREATE_EXPERIMENT_RUNS_SQL

pytestmark = pytest.mark.unit


def test_loader_accepts_jsonl_deduplicates_and_assigns_splits(tmp_path):
    path = tmp_path / "bank.jsonl"
    rows = [
        {
            "question": "¿Qué es POSEI?",
            "keywords": ["POSEI"],
            "reference_answer": "Un programa.",
            "category": "pac",
        },
        {
            "question": "  ¿QUÉ ES POSEI? ",
            "keywords": ["duplicada"],
            "reference_answer": "Duplicada.",
            "category": "pac",
        },
        {
            "question": "¿Qué exige BCAM 6?",
            "keywords": ["BCAM 6"],
            "reference_answer": "Cobertura.",
            "category": "bcam",
            "split": "holdout",
        },
    ]
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8"
    )

    assert len(load_tests(path)) == 2
    assert [item.question for item in load_tests(path, split="holdout")] == [
        "¿Qué exige BCAM 6?"
    ]


def test_default_question_bank_has_gold_schema():
    tests = load_tests()
    assert len(tests) >= 21
    categories = {item.category for item in tests}
    # Taxonomía del banco amplio versionado en gateway/core/tests.jsonl
    required = {
        "direct_fact",
        "temporal",
        "relationship",
        "spanning",
        "comparative",
        "numerical",
        "holistic",
    }
    assert required <= categories
    from collections import Counter
    counts = Counter(item.category for item in tests if item.category in required)
    assert all(n >= 3 for n in counts.values()), counts
    for item in tests:
        assert item.question.strip()
        assert item.keywords
        assert item.reference_answer.strip()
        assert item.category.strip()


def test_merge_test_banks_enriches_file_questions_and_appends_annotated():
    file_tests = [
        TestQuestion(
            question="¿Qué es POSEI?",
            keywords=["POSEI"],
            reference_answer="",
            category="pac",
        )
    ]
    merged = merge_test_banks(
        file_tests,
        [
            {
                "question": "¿Qué es POSEI?",
                "keywords": [],
                "reference_answer": "Ayudas a Canarias.",
                "selected_chunk_ids": ["chunk-1"],
                "flag_out_of_knowledge": False,
                "category": "pac",
            },
            {
                "question": "¿Cuál es el chunk correcto del tomate?",
                "keywords": ["tomate"],
                "reference_answer": "El anexo III.",
                "selected_chunk_ids": ["chunk-9"],
                "category": "direct_fact",
                "split": "dev",
                "flag_out_of_knowledge": False,
            },
        ],
    )

    assert len(merged) == 2
    posei = merged[0]
    assert posei.reference_answer == "Ayudas a Canarias."
    assert posei.metadata["expected_chunk_ids"] == ["chunk-1"]
    assert posei.metadata["source"] == "merged"
    assert merged[1].metadata["source"] == "annotated"


def test_merge_test_banks_preserves_hitl_source():
    merged = merge_test_banks(
        [],
        [
            {
                "question": "¿Qué es una SAT?",
                "keywords": ["SAT"],
                "reference_answer": "Sociedad Agraria de Transformación.",
                "selected_chunk_ids": [],
                "category": "sat",
                "metadata": {"source": "hitl", "document_id": "doc-1"},
            }
        ],
    )
    assert len(merged) == 1
    assert merged[0].metadata["source"] == "hitl"


def test_simulator_save_accepts_singular_selected_chunk_id():
    payload = SimulatorSaveRequest(
        question="¿Cuál es el protocolo?",
        selected_chunk_id="chunk-42",
        flags={"different_info": False, "out_of_knowledge": False},
    )
    assert payload.selected_chunk_ids == ["chunk-42"]


def test_experiment_runs_schema_tracks_embedding_and_distance():
    sql = CREATE_EXPERIMENT_RUNS_SQL.lower()
    assert "rag_experiment_runs" in sql
    assert "embedding_model" in sql
    assert "distance_metric" in sql
    assert "mrr" in sql
    assert "ndcg" in sql
    assert "precision_at_k" in sql


def test_upsert_test_question_jsonl_appends_hitl_fields(tmp_path):
    path = tmp_path / "bank.jsonl"
    path.write_text(
        json.dumps(
            {
                "question": "¿Qué es POSEI?",
                "keywords": ["Alejamiento"],
                "reference_answer": "Programa de opciones específicas.",
                "category": "direct_fact",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    upsert_test_question_jsonl(
        question="¿Qué medida cubre el plátano IGP?",
        keywords=["Medida II", "plátano"],
        reference_answer="La Medida II.",
        category="direct_fact",
        source_file="03_posei_medidas.md",
        path=path,
    )
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 2
    added = rows[1]
    assert added["question"] == "¿Qué medida cubre el plátano IGP?"
    assert added["keywords"] == ["Medida II", "plátano"]
    assert added["reference_answer"] == "La Medida II."
    assert added["category"] == "direct_fact"
    loaded = load_tests(path)
    assert len(loaded) == 2
    assert loaded[1].keywords == ["Medida II", "plátano"]
