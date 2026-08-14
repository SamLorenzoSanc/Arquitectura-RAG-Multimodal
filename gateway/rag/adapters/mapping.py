from rag.domain.entities import RetrievedChunk
from schemas.chat import Result


def to_result(chunk: RetrievedChunk) -> Result:
    return Result(page_content=chunk.page_content, metadata=dict(chunk.metadata or {}))


def from_result(result: Result) -> RetrievedChunk:
    return RetrievedChunk(
        page_content=result.page_content, metadata=dict(result.metadata or {})
    )


def to_results(chunks: list[RetrievedChunk]) -> list[Result]:
    return [to_result(chunk) for chunk in chunks]


def bundle_to_dict(bundle) -> dict:
    return {
        "chunks": to_results(bundle.chunks),
        "rewritten_query": bundle.rewritten_query,
        "dense_original": to_results(bundle.dense_original),
        "dense_rewritten": to_results(bundle.dense_rewritten),
        "bm25_original": to_results(bundle.bm25_original),
        "bm25_rewritten": to_results(bundle.bm25_rewritten),
        "candidates": to_results(bundle.candidates),
        "retrieval": bundle.retrieval,
        "_cache_scope": bundle.cache_scope,
    }
