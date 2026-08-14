from types import SimpleNamespace

import pytest

from rag.application.answer import AnswerQuestion
from rag.application.evaluate import EvaluateRetrieval, calculate_mrr
from rag.application.ingest import IngestDocument
from rag.application.retrieve import HybridRetrieve, invalidate_retrieval_cache
from rag.domain.entities import RetrievalQuery, RetrievedChunk
from rag.domain.fusion import rrf_fusion
from rag.domain.lexicon import expand_agro_query, should_rewrite_query, tokenize
from schemas.chat import Result
from schemas.evaluation import AnswerEvaluation
from services.rag_service import RAGService

pytestmark = pytest.mark.unit


def _chunk(cid: str, text: str, source: str = "dense", doc: str = "d") -> RetrievedChunk:
    return RetrievedChunk(
        page_content=text,
        metadata={
            "chunk_id": cid,
            "document_id": doc,
            "retrieval_source": source,
            "source": f"{cid}.pdf",
        },
    )


class FakeChunks:
    def __init__(self):
        self.calls: list[tuple[str, str, list[str] | None]] = []

    async def retrieve_dense(
        self,
        question,
        tenant_id,
        collections,
        *,
        k,
        distance_metric="cosine",
        embedding_model=None,
    ):
        self.calls.append((question, tenant_id, collections))
        kb = (collections or ["all"])[0]
        return [_chunk(kb, f"{question}-{kb}")]


class FakeLexical:
    def __init__(self):
        self.invalidated: list[str | None] = []
        self.rebuilt: list[str] = []

    async def retrieve(self, question, tenant_id, collections, *, k):
        return []

    async def rebuild(self, tenant_id: str) -> None:
        self.rebuilt.append(tenant_id)

    def invalidate(self, tenant_id: str | None = None) -> None:
        self.invalidated.append(tenant_id)


class FakeLlm:
    def __init__(self, answer: str = "Diagnóstico: riego."):
        self.answer = answer
        self.complete_calls = []
        self.parse_calls = []

    async def complete(self, model, messages):
        self.complete_calls.append((model, messages))
        return self.answer

    async def parse(self, model, messages, response_format):
        self.parse_calls.append(messages)
        return AnswerEvaluation(
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


class IdentityReranker:
    def rerank(self, question, chunks):
        return list(chunks)


def test_expand_agro_query_adds_irrigation_synonyms():
    expanded = expand_agro_query("problema de riego en invernadero")
    assert "irrigación" in expanded
    assert "gotero" in expanded


def test_tokenize_strips_accents_and_punctuation():
    assert "platano" in tokenize("Plátano, riego.")
    assert should_rewrite_query("compara las ayudas POSEI y las de la PAC en Canarias")
    assert not should_rewrite_query("qué es el POSEI")


def test_rrf_fusion_ranks_chunk_present_in_several_lists_first():
    shared = _chunk("1", "norma posei", "dense")
    only_bm25 = _chunk("2", "otro texto", "bm25")
    fused = rrf_fusion([shared], [shared], [shared], [only_bm25], rrf_k=60, candidate_k=10)
    assert fused[0].metadata["chunk_id"] == "1"
    assert fused[0].metadata["rrf_score"] > fused[1].metadata["rrf_score"]


@pytest.mark.asyncio
async def test_hybrid_retrieve_and_answer_use_fake_ports_without_io():
    chunks = FakeChunks()
    lexical = FakeLexical()
    llm = FakeLlm()
    retrieve = HybridRetrieve(
        chunks, lexical, llm, IdentityReranker(), retrieval_k=3, bm25_k=3, final_k=3
    )
    invalidate_retrieval_cache()
    bundle = await retrieve.execute(
        RetrievalQuery(question="riego", tenant_id="t1", collections=["kb-a"])
    )
    assert bundle.chunks[0].page_content == "riego-kb-a"
    assert len(chunks.calls) == 1

    cached = await retrieve.execute(
        RetrievalQuery(question="riego", tenant_id="t1", collections=["kb-a"])
    )
    assert cached.chunks[0].page_content == "riego-kb-a"
    assert len(chunks.calls) == 1

    answerer = AnswerQuestion(retrieve, llm, "llama-test")
    result = await answerer.execute("riego", tenant_id="t1", collections=["kb-a"])
    assert result["answer"] == "Diagnóstico: riego."
    assert llm.complete_calls
    assert result["chunks"][0].page_content == "riego-kb-a"


@pytest.mark.asyncio
async def test_ingest_and_evaluate_retrieval_with_fakes():
    lexical = FakeLexical()
    ingest = IngestDocument(lexical)
    await ingest.execute("tenant-z")
    assert lexical.invalidated == ["tenant-z"]
    assert lexical.rebuilt == ["tenant-z"]

    retrieve = HybridRetrieve(
        FakeChunks(), FakeLexical(), FakeLlm(), IdentityReranker(), final_k=3
    )
    evaluator = EvaluateRetrieval(retrieve)
    test = SimpleNamespace(question="riego", keywords=["riego"])
    metrics = await evaluator.execute(test, "t1", ["kb-a"], k=3)
    assert metrics.keywords_found == 1
    assert calculate_mrr("riego", [Result(page_content="el riego gotero", metadata={})]) == 1.0


@pytest.mark.asyncio
async def test_cache_hit_kb_isolation_evaluation_bypass_and_invalidation():
    chunks = FakeChunks()
    retrieve = HybridRetrieve(
        chunks, FakeLexical(), FakeLlm(), IdentityReranker(), final_k=3
    )
    invalidate_retrieval_cache()
    query_a = RetrievalQuery(question="riego", tenant_id="tenant-a", collections=["kb-a"])
    query_b = RetrievalQuery(question="riego", tenant_id="tenant-a", collections=["kb-b"])
    await retrieve.execute(query_a)
    await retrieve.execute(query_a)
    assert len(chunks.calls) == 1
    await retrieve.execute(query_b)
    assert len(chunks.calls) == 2
    await retrieve.execute(
        RetrievalQuery(
            question="riego",
            tenant_id="tenant-a",
            collections=["kb-a"],
            evaluation_mode=True,
        )
    )
    assert len(chunks.calls) == 3
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
    )
    assert "Respuesta de referencia" in captured["prompt"]
    assert "Contexto recuperado" in captured["prompt"]
    assert result.numeric_match == 1
    assert result.citation_accuracy == 1
