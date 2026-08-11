"""Tests unitarios del mapeo de perfil agricultor y cola de ingesta."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from clients.inference_client import resolve_llm_base_url
from clients.retrieval_client import retrieval_service_enabled
from services.farmer_context_service import (
    format_parcel_markdown,
    map_crop_to_product_id,
    map_island_to_code,
)
from services.queue_service import enqueue_ingest_job, ingest_queue_enabled

pytestmark = pytest.mark.unit


def test_map_crop_and_island():
    assert map_crop_to_product_id("Plátano Canarias") == "platano_canarias"
    assert map_crop_to_product_id("Tomate Daniela") == "tomate"
    assert map_crop_to_product_id(None) == "platano_canarias"
    assert map_island_to_code("La Palma") == "La_Palma"
    assert map_island_to_code(None) == "La_Palma"


def test_format_parcel_markdown_includes_cultivo():
    md = format_parcel_markdown(
        {
            "id": "c1",
            "nombre": "Finca Demo",
            "cultivo": "Plátano",
            "isla": "La Palma",
            "lat": 28.68,
            "lon": -17.76,
            "sistema_riego": "Goteo",
        },
        treatments=[
            {
                "producto": "Oillette",
                "fecha": "2026-03-12",
                "carencia_dias": 3,
            }
        ],
    )
    assert "Finca Demo" in md
    assert "Plátano" in md
    assert "Oillette" in md


def test_resolve_llm_prefers_inference_url(monkeypatch):
    monkeypatch.setenv("INFERENCE_URL", "http://inference:50051")
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    assert resolve_llm_base_url() == "http://inference:50051/v1"


def test_resolve_llm_falls_back_to_ollama(monkeypatch):
    monkeypatch.delenv("INFERENCE_URL", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434/v1")
    assert resolve_llm_base_url() == "http://ollama:11434/v1"


def test_retrieval_flag_requires_url(monkeypatch):
    with patch("clients.retrieval_client.USE_RETRIEVAL_SERVICE", True), patch(
        "clients.retrieval_client.RETRIEVAL_URL", ""
    ):
        assert retrieval_service_enabled() is False
    with patch("clients.retrieval_client.USE_RETRIEVAL_SERVICE", True), patch(
        "clients.retrieval_client.RETRIEVAL_URL", "http://retrieval:50052"
    ):
        assert retrieval_service_enabled() is True


def test_enqueue_disabled_by_default(monkeypatch):
    monkeypatch.setenv("USE_INGEST_QUEUE", "false")
    # re-read module flag via function that checks env... ingest_queue_enabled
    # uses module-level USE_INGEST_QUEUE captured at import; patch it
    with patch("services.queue_service.USE_INGEST_QUEUE", False):
        assert ingest_queue_enabled() is False
        assert enqueue_ingest_job("doc", "job") is False


def test_enqueue_pushes_redis_when_enabled():
    fake = MagicMock()
    with (
        patch("services.queue_service.USE_INGEST_QUEUE", True),
        patch("services.queue_service.get_redis", return_value=fake),
    ):
        assert enqueue_ingest_job("doc-1", "job-1") is True
        fake.lpush.assert_called_once()
        args = fake.lpush.call_args[0]
        payload = json.loads(args[1])
        assert payload["document_id"] == "doc-1"
        assert payload["job_id"] == "job-1"
