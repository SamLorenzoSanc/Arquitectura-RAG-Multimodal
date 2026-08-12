import pytest

from core.test import load_tests
from services.evaluation_metrics import normalize_text

pytestmark = pytest.mark.unit


def test_reference_answers_are_not_embedded_in_questions():
    leaked = [
        test.question
        for test in load_tests()
        if normalize_text(test.reference_answer) in normalize_text(test.question)
    ]
    assert leaked == []
