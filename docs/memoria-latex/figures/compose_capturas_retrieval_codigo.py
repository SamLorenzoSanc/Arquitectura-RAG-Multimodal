"""Capturas de código del retrieval híbrido (defensa / memoria TFM)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "compose_capturas_ocr_codigo.py"

spec = importlib.util.spec_from_file_location("ocr_caps", HELPER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

compose_code_capture = mod.compose_code_capture
OUT_DIR = ROOT
PRESENT = ROOT.parent.parent / "presentacion_defensa"


def main():
    # Captura principal para diapositiva: núcleo HybridRetrieve.execute
    compose_code_capture(
        filename="captura-codigo-retrieval-hibrido.png",
        title="HybridRetrieve.execute — denso ∥ BM25 → RRF → top-k",
        subtitle="gateway/rag/application/retrieve.py · caso de uso del Alg. 2",
        start_line=143,
        lines=[
            "t_retrieval = time.time()",
            "if rewritten == question:",
            "    dense_original, bm25_original = await self._parallel_pair(",
            "        question,",
            "        query.tenant_id,",
            "        query.collections,",
            "        metric,",
            "        expand_lexical=expand_lexical,",
            "    )",
            "    dense_rewritten = dense_original",
            "    bm25_rewritten = bm25_original",
            "else:",
            "    dense_original, dense_rewritten, bm25_original, bm25_rewritten = (",
            "        await self._parallel_four(",
            "            question, rewritten, query.tenant_id,",
            "            query.collections, metric,",
            "            expand_lexical=expand_lexical,",
            "        )",
            "    )",
            "",
            "candidates = rrf_fusion(",
            "    dense_original,",
            "    dense_rewritten,",
            "    bm25_original,",
            "    bm25_rewritten,",
            "    rrf_k=self.rrf_k,",
            "    candidate_k=self.candidate_k,",
            ")",
            "ranked = (",
            "    self.reranker.rerank(question, candidates) if do_rerank",
            "    else candidates",
            ")",
            "final_chunks = ranked[: self.final_k]",
        ],
    )

    compose_code_capture(
        filename="captura-codigo-hybrid-retrieve-class.png",
        title="HybridRetrieve — puertos y parámetros",
        subtitle="Inyección hexagonal: ChunkRepository + LexicalIndexPort + RRF",
        start_line=54,
        lines=[
            "class HybridRetrieve:",
            "    \"\"\"Caso de uso: Dense + BM25 + RRF (+ rerank opcional).\"\"\"",
            "",
            "    def __init__(",
            "        self,",
            "        chunks: ChunkRepository,",
            "        lexical: LexicalIndexPort,",
            "        llm: LlmPort,",
            "        reranker: RerankerPort,",
            "        *,",
            "        retrieval_k: int = 10,",
            "        bm25_k: int = 10,",
            "        rrf_k: int = 60,",
            "        candidate_k: int = 15,",
            "        final_k: int = 3,",
            "        ...",
            "    ):",
            "        self.chunks = chunks      # pgvector (denso)",
            "        self.lexical = lexical    # BM25 (léxico)",
            "        self.rrf_k = rrf_k",
            "        self.final_k = final_k",
        ],
    )

    compose_code_capture(
        filename="captura-codigo-rrf-fusion.png",
        title="fusion.py — Reciprocal Rank Fusion",
        subtitle="gateway/rag/domain/fusion.py · score = 1/(k_rrf + rank)",
        start_line=50,
        lines=[
            "for ranking in lists:",
            "    for rank, chunk in enumerate(ranking, start=1):",
            "        key = chunk_key(chunk)",
            "        if key not in scores:",
            "            continue",
            "        scores[key] += 1.0 / (rrf_k + rank)",
            "        sources[key].add(",
            "            chunk.metadata.get(\"retrieval_source\", \"unknown\")",
            "        )",
            "",
            "ranked = sorted(scores, key=scores.get, reverse=True)",
            "for key in ranked[:candidate_k]:",
            "    chunk = merged[key]",
            "    metadata = dict(chunk.metadata)",
            "    metadata.update({",
            "        \"rrf_score\": scores[key],",
            "        \"rrf_sources\": sorted(sources[key]),",
            "    })",
            "    candidates.append(RetrievedChunk(...))",
        ],
    )

    compose_code_capture(
        filename="captura-codigo-parallel-pair.png",
        title="retrieve.py — _parallel_pair (asyncio.gather)",
        subtitle="pgvector + BM25 en paralelo sobre el mismo tenant",
        start_line=345,
        lines=[
            "return await asyncio.gather(",
            "    self.chunks.retrieve_dense(",
            "        question,",
            "        tenant_id,",
            "        collections,",
            "        k=self.retrieval_k,",
            "        distance_metric=metric,",
            "        embedding_model=self.embedding_model,",
            "    ),",
            "    self.lexical.retrieve(",
            "        expand_agro_query(question) if expand_lexical else question,",
            "        tenant_id,",
            "        collections,",
            "        k=self.bm25_k,",
            "    ),",
            ")",
        ],
    )

    PRESENT.mkdir(parents=True, exist_ok=True)
    for name in (
        "captura-codigo-retrieval-hibrido.png",
        "captura-codigo-hybrid-retrieve-class.png",
        "captura-codigo-rrf-fusion.png",
        "captura-codigo-parallel-pair.png",
    ):
        src = OUT_DIR / name
        (PRESENT / name).write_bytes(src.read_bytes())
        print(f"Copied -> {PRESENT / name}")


if __name__ == "__main__":
    main()
