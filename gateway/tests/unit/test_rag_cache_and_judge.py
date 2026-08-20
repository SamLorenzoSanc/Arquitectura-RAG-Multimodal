import pytest

from schemas.chat import Result
from schemas.evaluation import AnswerEvaluation
from services.rag_service import RAGService

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_cache_hit_kb_isolation_evaluation_bypass_and_invalidation(
    monkeypatch, tmp_path
):
    service = RAGService(bm25_index_dir=str(tmp_path))
    calls = 0

    async def retrieve_dense(question, tenant_id, collections=None, **_kwargs):
        nonlocal calls
        calls += 1
        kb = (collections or ["all"])[0]
        from rag.domain.entities import RetrievedChunk

        return [
            RetrievedChunk(
                page_content=f"{question}-{kb}",
                metadata={"chunk_id": kb, "document_id": "d"},
            )
        ]

    async def bm25(*args, **kwargs):
        return []

    monkeypatch.setattr(service._container.chunks, "retrieve_dense", retrieve_dense)
    monkeypatch.setattr(service._container.lexical, "retrieve", bm25)
    RAGService.invalidate_retrieval_cache()

    await service.fetch_context("riego", "tenant-a", ["kb-a"])
    await service.fetch_context("riego", "tenant-a", ["kb-a"])
    assert calls == 1
    await service.fetch_context("riego", "tenant-a", ["kb-b"])
    assert calls == 2
    await service.fetch_context("riego", "tenant-a", ["kb-a"], evaluation_mode=True)
    assert calls == 3
    assert RAGService.invalidate_retrieval_cache("tenant-a") == 2


@pytest.mark.asyncio
async def test_judge_receives_reference_context_and_overrides_deterministic_scores(
    monkeypatch,
):
    service = RAGService()
    parsed = AnswerEvaluation(
        feedback="ok",
        accuracy=5,
        completeness=5,
        relevance=5,
        faithfulness=5,
        groundedness=5,
        citation_accuracy=0,
        numeric_match=0,
        abstention=0,
    )
    captured = {}

    async def parse(model, messages, response_format):
        captured["prompt"] = messages[-1]["content"]
        return parsed

    monkeypatch.setattr(service._container.llm, "parse", parse)
    result, _, _ = await service.evaluate_answer(
        "¿Importe?",
        "Según [posei.pdf], 1.200 €.",
        [Result(page_content="La ayuda es 1.200 €.", metadata={"source": "posei.pdf"})],
        reference_answer="La ayuda es 1.200 €.",
        keywords=["1.200"],
    )
    assert "Respuesta de referencia" in captured["prompt"]
    assert "Contexto recuperado" in captured["prompt"]
    assert "Palabras clave esperadas" in captured["prompt"]
    assert result.numeric_match == 1
    assert result.citation_accuracy == 1
    assert result.keyword_coverage == 100.0
