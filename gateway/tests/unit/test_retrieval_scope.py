from rag.adapters.outbound.scope import dataset_row_text, is_uuid

import pytest

pytestmark = pytest.mark.unit


def test_is_uuid_accepts_canonical_ids():
    assert is_uuid("36feb70f-1111-4120-a8e2-3d401e3a84cf")
    assert not is_uuid("global")
    assert not is_uuid("")


def test_dataset_row_text_includes_prompt_context_and_answer():
    text = dataset_row_text(
        {
            "dataset_name": "Estatutos",
            "prompt": "¿Cuál es el objeto social?",
            "context": [{"page_content": "La cooperativa tiene por objeto..."}],
            "expected_response": "Producir y comercializar plátano.",
            "response": None,
        }
    )
    assert "Estatutos" in text
    assert "objeto social" in text
    assert "cooperativa" in text
    assert "plátano" in text
