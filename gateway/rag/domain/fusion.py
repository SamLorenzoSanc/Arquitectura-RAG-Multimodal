from __future__ import annotations

from rag.domain.entities import RetrievedChunk


def chunk_key(chunk: RetrievedChunk) -> tuple[str, str]:
    meta = chunk.metadata or {}
    return (
        str(meta.get("document_id", "")),
        str(meta.get("chunk_id", "") or chunk.page_content),
    )


def merge_unique(*lists: list[RetrievedChunk]) -> dict[tuple[str, str], RetrievedChunk]:
    merged: dict[tuple[str, str], RetrievedChunk] = {}
    for chunks in lists:
        for chunk in chunks:
            key = chunk_key(chunk)
            if key not in merged:
                merged[key] = chunk
                continue
            old = merged[key]
            if "dense" in chunk.metadata.get("retrieval_source", ""):
                if "distance" not in old.metadata:
                    merged[key] = chunk
    return merged


def rrf_fusion(
    dense_original: list[RetrievedChunk],
    dense_rewritten: list[RetrievedChunk],
    bm25_original: list[RetrievedChunk],
    bm25_rewritten: list[RetrievedChunk],
    *,
    rrf_k: int = 60,
    candidate_k: int = 15,
) -> list[RetrievedChunk]:
    rankings = [dense_original, dense_rewritten, bm25_original, bm25_rewritten]
    lists: list[list[RetrievedChunk]] = []
    seen_objects: set[int] = set()
    for ranking in rankings:
        if not ranking or id(ranking) in seen_objects:
            continue
        seen_objects.add(id(ranking))
        lists.append(ranking)
    merged = merge_unique(*lists)
    scores: dict[tuple[str, str], float] = {key: 0.0 for key in merged}
    sources: dict[tuple[str, str], set[str]] = {key: set() for key in merged}

    for ranking in lists:
        for rank, chunk in enumerate(ranking, start=1):
            key = chunk_key(chunk)
            if key not in scores:
                continue
            scores[key] += 1.0 / (rrf_k + rank)
            sources[key].add(chunk.metadata.get("retrieval_source", "unknown"))

    ranked = sorted(scores, key=scores.get, reverse=True)
    candidates: list[RetrievedChunk] = []
    for key in ranked[:candidate_k]:
        chunk = merged[key]
        metadata = dict(chunk.metadata)
        metadata.update({"rrf_score": scores[key], "rrf_sources": sorted(sources[key])})
        candidates.append(
            RetrievedChunk(page_content=chunk.page_content, metadata=metadata)
        )
    return candidates
