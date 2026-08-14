from __future__ import annotations

import time
from threading import Lock

from rag.domain.entities import RetrievedChunk

_RERANKERS: dict[str, object] = {}
_RERANKERS_LOCK = Lock()


class IdentityReranker:
    def rerank(
        self, question: str, chunks: list[RetrievedChunk]
    ) -> list[RetrievedChunk]:
        return list(chunks)


class CrossEncoderReranker:
    def __init__(
        self, model_name: str = "BAAI/bge-reranker-v2-m3", batch_size: int = 16
    ):
        self.model_name = model_name
        self.batch_size = batch_size
        self._reranker = None

    def _get(self):
        import torch
        from sentence_transformers import CrossEncoder

        device = "cuda" if torch.cuda.is_available() else "cpu"
        cache_key = f"{self.model_name}:{device}"
        if self._reranker is None:
            with _RERANKERS_LOCK:
                if cache_key not in _RERANKERS:
                    _RERANKERS[cache_key] = CrossEncoder(
                        self.model_name, device=device, max_length=512
                    )
                self._reranker = _RERANKERS[cache_key]
        return self._reranker

    def rerank(
        self, question: str, chunks: list[RetrievedChunk]
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []
        t0 = time.time()
        reranker = self._get()
        pairs = [(question, chunk.page_content) for chunk in chunks]
        scores = reranker.predict(
            pairs, batch_size=self.batch_size, show_progress_bar=False
        )
        ranked = sorted(
            zip(chunks, scores), key=lambda item: float(item[1]), reverse=True
        )
        final: list[RetrievedChunk] = []
        for chunk, score in ranked:
            metadata = dict(chunk.metadata)
            metadata["cross_encoder_score"] = float(score)
            metadata["retrieval_source"] = "hybrid"
            final.append(
                RetrievedChunk(page_content=chunk.page_content, metadata=metadata)
            )
        _ = t0
        return final
