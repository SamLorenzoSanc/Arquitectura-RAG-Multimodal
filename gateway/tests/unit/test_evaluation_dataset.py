import json

import pytest

from core.test import load_tests

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
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")

    assert len(load_tests(path)) == 2
    assert [item.question for item in load_tests(path, split="holdout")] == ["¿Qué exige BCAM 6?"]


def test_canonical_dataset_has_no_duplicate_questions_and_has_holdout():
    tests = load_tests()
    assert len(tests) > 0
    assert len({test.question.casefold().strip() for test in tests}) == len(tests)
    assert {"dev", "holdout"}.issubset({test.split for test in tests})
