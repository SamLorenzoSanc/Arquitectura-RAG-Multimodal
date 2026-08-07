from __future__ import annotations

import math
import pickle
import re
import time
import unicodedata
from pathlib import Path
from threading import Lock
import torch
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from sqlalchemy import select
from tenacity import wait_exponential
import asyncio
import time
from services.database import AsyncSessionLocal
from schemas.chat import Result
from models.chunk import Chunk
from models.document import Document
from models.embedding import Embedding

load_dotenv(override=True)
WAIT_POLICY = wait_exponential(multiplier=1, min=10, max=240)


class RetrievalEval(BaseModel):
    mrr: float = Field(description="Mean Reciprocal Rank")
    ndcg: float = Field(description="Normalized Discounted Cumulative Gain")
    keywords_found: int = Field(description="Número de keywords encontradas")
    total_keywords: int = Field(description="Número total de keywords")
    keyword_coverage: float = Field(description="Cobertura porcentual de keywords")
    accuracy: float = Field(description="Acierto globales de la búsqueda")


class AnswerEval(BaseModel):
    feedback: str = Field(description="Comentarios sobre la respuesta")
    accuracy: float = Field(description="Precisión factual de 1 a 5")
    completeness: float = Field(description="Exhaustividad de 1 a 5")
    relevance: float = Field(description="Pertinencia de 1 a 5")


class RAGService:
    """RAG híbrido multitenant: Dense + BM25 + RRF + Cross-Encoder."""

    SYSTEM_PROMPT = """
    Eres un asistente experto y amable que representa a la empresa AgroTech.
    Si el usuario pregunta por información contenida en el contexto, RESPÓNDELA con precisión técnica y profesional.
    No te niegues a responder información técnica o corporativa si esta se encuentra dentro del Contexto facilitado.
    No añadas avisos de confidencialidad a menos que el documento mismo los contenga explícitamente.
    REGLA CRÍTICA DE IDIOMA: Debe responder SIEMPRE en español.
    No inventes datos que no estén respaldados por el contexto proporcionado.
    Contexto:
    {context}
    """

    # Cross-Encoder multilingüe adecuado para un corpus en español.
    # Se descarga de Hugging Face la primera vez que se instancia.
    DEFAULT_RERANKER = "BAAI/bge-reranker-v2-m3"

    def __init__(
        self,
        model: str = "llama3",
        embedding_model: str = "qwen3-embedding:latest",
        retrieval_k: int = 10,
        bm25_k: int = 10,
        rrf_k: int = 60,
        candidate_k: int = 15,
        final_k: int = 3,
        reranker_model: str = DEFAULT_RERANKER,
        reranker_batch_size: int = 16,
        bm25_index_dir: str | None = None,
    ):
        self.model = model
        self.embedding_model = embedding_model
        self.retrieval_k = retrieval_k
        self.bm25_k = bm25_k
        self.rrf_k = rrf_k
        self.candidate_k = candidate_k
        self.final_k = final_k
        self.reranker_model = reranker_model
        self.reranker_batch_size = reranker_batch_size
        self.wait = WAIT_POLICY

        self.client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        )

        # Por defecto se comparte el directorio con el servicio de ingesta.
        self.bm25_index_dir = Path(
            bm25_index_dir or Path(__file__).resolve().parent / "bm25_indexes"
        )
        self.bm25_index_dir.mkdir(parents=True, exist_ok=True)

        self._bm25_cache: dict[str, tuple[float, BM25Okapi, list[dict]]] = {}
        self._bm25_lock = Lock()
        self._reranker: CrossEncoder | None = None

    def get_embeddings(self):
        return self.embedding_model

    @staticmethod
    def _normalize_text(text: str | None) -> str:
        """Normalización léxica estable para BM25 en español."""
        text = text or ""
        text = unicodedata.normalize("NFKC", text).lower()
        text = "".join(
            c
            for c in unicodedata.normalize("NFKD", text)
            if not unicodedata.combining(c)
        )
        return text

    @classmethod
    def _tokenize(cls, text: str | None) -> list[str]:
        text = cls._normalize_text(text)
        # Conserva palabras, números y expresiones con guion/barra.
        return re.findall(r"[^\W_]+(?:[-/][^\W_]+)*", text, flags=re.UNICODE)

    @staticmethod
    def _chunk_key(chunk: Result) -> tuple[str, str]:
        return (
            chunk.metadata.get("document_id", ""),
            chunk.metadata.get("chunk_id", "") or chunk.page_content,
        )

    @staticmethod
    def _safe_filename(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", value)

    def _bm25_path(self, tenant_id: str) -> Path:
        return self.bm25_index_dir / f"tenant_{self._safe_filename(str(tenant_id))}.pkl"

    def _load_bm25_file(self, tenant_id: str):
        path = self._bm25_path(tenant_id)
        if not path.exists():
            return None
        try:
            with path.open("rb") as fh:
                payload = pickle.load(fh)
            if not isinstance(payload, dict) or "documents" not in payload:
                return None
            documents = payload["documents"]
            corpus = [self._tokenize(d["text"]) for d in documents]
            if not corpus:
                return None
            return BM25Okapi(corpus), documents, path.stat().st_mtime
        except Exception as exc:
            print(f"      [BM25] No se pudo cargar índice {path}: {exc}")
            return None

    async def _build_bm25_from_db(self, tenant_id: str):
        """Construye un índice BM25 por tenant desde PostgreSQL.

        El índice contiene todos los chunks del tenant y conserva knowledge_base_id
        para aplicar el filtro multitenant/multicorpus durante la recuperación.
        """
        stmt = (
            select(Chunk, Document)
            .join(Document, Document.id == Chunk.document_id)
            .where(Document.tenant_id == tenant_id)
            .order_by(Document.id, Chunk.position)
        )

        async with AsyncSessionLocal() as session:
            result_proxy = await session.execute(stmt)
            rows = result_proxy.all()

        documents = []
        for chunk, document in rows:
            text = "\n".join(
                part for part in [chunk.headline, chunk.summary, chunk.content] if part
            )
            documents.append(
                {
                    "chunk_id": str(chunk.id),
                    "document_id": str(document.id),
                    "tenant_id": str(document.tenant_id),
                    "knowledge_base_id": str(document.knowledge_base_id),
                    "source": document.filename,
                    "type": document.mime_type,
                    "position": chunk.position,
                    "text": text,
                }
            )

        payload = {
            "version": 1,
            "tenant_id": str(tenant_id),
            "documents": documents,
            "created_at": time.time(),
        }
        path = self._bm25_path(tenant_id)
        tmp_path = path.with_suffix(".tmp")
        with tmp_path.open("wb") as fh:
            pickle.dump(payload, fh, protocol=pickle.HIGHEST_PROTOCOL)
        tmp_path.replace(path)

        corpus = [self._tokenize(d["text"]) for d in documents]
        if not corpus:
            return None
        return BM25Okapi(corpus), documents, path.stat().st_mtime

    def should_rewrite_query(self, question: str) -> bool:
        """
        Decide si merece la pena utilizar el LLM para reescribir la consulta.

        Se evita el rewriting en consultas:
        - Cortas.
        - Directas.
        - Con nombres propios.
        - Con identificadores.
        - Con preguntas factuales sencillas.

        El objetivo es ahorrar varios segundos de latencia
        sin alterar el pipeline híbrido.
        """

        q = " ".join(question.strip().split())

        if not q:
            return False

        # ------------------------------------------------------------
        # 1. Consultas muy cortas
        # ------------------------------------------------------------
        words = q.split()

        if len(words) <= 10:
            return False

        # ------------------------------------------------------------
        # 2. Patrones que normalmente no necesitan rewriting
        # ------------------------------------------------------------
        simple_patterns = (
            "cuál es",
            "cual es",
            "quién es",
            "quien es",
            "qué es",
            "que es",
            "dónde está",
            "donde esta",
            "cuándo",
            "cuando",
            "cuánto",
            "cuanto",
            "cuántos",
            "cuantos",
            "cuántas",
            "cuantas",
            "qué fecha",
            "que fecha",
            "qué número",
            "que numero",
        )

        q_lower = q.lower()

        if any(q_lower.startswith(pattern) for pattern in simple_patterns):
            return False

        # ------------------------------------------------------------
        # 3. Si parece una consulta de síntesis/comparación,
        #    sí utilizamos rewriting.
        # ------------------------------------------------------------
        complex_patterns = (
            "compara",
            "comparar",
            "diferencia entre",
            "diferencias entre",
            "relaciona",
            "relacionar",
            "explica cómo",
            "explica como",
            "explica por qué",
            "explica por que",
            "analiza",
            "analizar",
            "resume",
            "resumir",
            "sintetiza",
            "sintetizar",
            "teniendo en cuenta",
            "a partir de",
            "qué relación",
            "que relacion",
            "cómo afecta",
            "como afecta",
            "en qué medida",
            "en que medida",
        )

        if any(pattern in q_lower for pattern in complex_patterns):
            return True

        if len(words) > 25:
            return True

        return False

    async def _get_bm25_index(self, tenant_id: str):
        """Carga el índice persistido o lo reconstruye si no existe."""
        path = self._bm25_path(tenant_id)
        mtime = path.stat().st_mtime if path.exists() else None
        cache = self._bm25_cache.get(str(tenant_id))

        if cache and mtime is not None and cache[0] == mtime:
            return cache[1], cache[2]

        with self._bm25_lock:
            loaded = self._load_bm25_file(tenant_id)
        if loaded is None:
            loaded = await self._build_bm25_from_db(tenant_id)
            if loaded is None:
                return None, []

        bm25, documents, loaded_mtime = loaded
        self._bm25_cache[str(tenant_id)] = (loaded_mtime, bm25, documents)
        return bm25, documents

    def invalidate_bm25_cache(self, tenant_id: str | None = None):
        if tenant_id is None:
            self._bm25_cache.clear()
        else:
            self._bm25_cache.pop(str(tenant_id), None)

    def rewrite_query(self, question: str, history: list | None = None) -> str:
        t0 = time.time()
        history = history or []
        prompt = f"""
            Historial:
            {history}
            Pregunta:
            {question}
            Respuesta en español.
            Reescribe únicamente la consulta.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": prompt}],
        )
        rewritten = response.choices[0].message.content.strip()
        print(f"      Consulta reescrita en {time.time()-t0:.2f}s: '{rewritten}'")
        return rewritten

    async def retrieve(
        self,
        question: str,
        tenant_id: str,
        collections: list[str] | None = None,
    ) -> list[Result]:
        """Dense retrieval mediante pgvector, manteniendo el filtro multitenant."""
        t0 = time.time()
        raw_embedding = (
            self.client.embeddings.create(
                model=self.embedding_model,
                input=[question],
            )
            .data[0]
            .embedding
        )
        t_emb = time.time() - t0

        stmt = (
            select(
                Chunk,
                Document,
                Embedding.vector.cosine_distance(raw_embedding).label("distance"),
            )
            .join(Embedding, Embedding.chunk_id == Chunk.id)
            .join(Document, Document.id == Chunk.document_id)
            .where(Document.tenant_id == tenant_id)
        )

        if collections:
            stmt = stmt.where(Document.knowledge_base_id.in_(collections))

        stmt = stmt.order_by(Embedding.vector.cosine_distance(raw_embedding)).limit(
            self.retrieval_k
        )

        async with AsyncSessionLocal() as session:
            result_proxy = await session.execute(stmt)
            rows = result_proxy.all()

        results = []
        for chunk, document, distance in rows:
            results.append(
                Result(
                    page_content="\n\n".join(
                        part
                        for part in [chunk.headline, chunk.summary, chunk.content]
                        if part
                    ).strip(),
                    metadata={
                        "chunk_id": str(chunk.id),
                        "document_id": str(document.id),
                        "tenant_id": str(document.tenant_id),
                        "knowledge_base_id": str(document.knowledge_base_id),
                        "source": document.filename,
                        "type": document.mime_type,
                        "distance": float(distance),
                        "retrieval_source": "dense",
                    },
                )
            )

        print(
            f"      [DENSE] Embedding {t_emb:.2f}s | {len(results)} chunks | "
            f"tenant={tenant_id} | collections={collections}"
        )
        return results

    async def retrieve_bm25(
        self,
        question: str,
        tenant_id: str,
        collections: list[str] | None = None,
    ) -> list[Result]:
        """BM25 independiente del dense retrieval, con filtrado por tenant/KB."""
        t0 = time.time()
        bm25, documents = await self._get_bm25_index(tenant_id)
        if bm25 is None:
            return []

        query_tokens = self._tokenize(question)
        if not query_tokens:
            return []

        scores = bm25.get_scores(query_tokens)
        allowed = set(map(str, collections)) if collections else None

        ranked_indices = sorted(
            range(len(documents)),
            key=lambda i: float(scores[i]),
            reverse=True,
        )

        results = []
        for idx in ranked_indices:
            meta = documents[idx]
            score = float(scores[idx])
            if score <= 0:
                continue
            if allowed is not None and meta["knowledge_base_id"] not in allowed:
                continue

            results.append(
                Result(
                    page_content=meta["text"],
                    metadata={
                        **meta,
                        "bm25_score": score,
                        "retrieval_source": "bm25",
                    },
                )
            )
            if len(results) >= self.bm25_k:
                break

        print(
            f"      [BM25] {len(results)} chunks | {time.time()-t0:.2f}s | "
            f"tenant={tenant_id} | collections={collections}"
        )
        return results

    def _merge_unique(self, *lists: list[Result]) -> dict[tuple[str, str], Result]:
        merged: dict[tuple[str, str], Result] = {}
        for chunks in lists:
            for chunk in chunks:
                key = self._chunk_key(chunk)
                if key not in merged:
                    merged[key] = chunk
                else:
                    # Conservamos la versión que tenga más información de ranking.
                    old = merged[key]
                    if "dense" in chunk.metadata.get("retrieval_source", ""):
                        if "distance" not in old.metadata:
                            merged[key] = chunk
        return merged

    def rrf_fusion(
        self,
        dense_original: list[Result],
        dense_rewritten: list[Result],
        bm25_original: list[Result],
        bm25_rewritten: list[Result],
    ) -> list[Result]:
        """Reciprocal Rank Fusion sobre las cuatro listas de recuperación."""
        lists = [
            dense_original,
            dense_rewritten,
            bm25_original,
            bm25_rewritten,
        ]
        merged = self._merge_unique(*lists)
        scores: dict[tuple[str, str], float] = {key: 0.0 for key in merged}
        sources: dict[tuple[str, str], set[str]] = {key: set() for key in merged}

        for ranking in lists:
            for rank, chunk in enumerate(ranking, start=1):
                key = self._chunk_key(chunk)
                if key not in scores:
                    continue
                scores[key] += 1.0 / (self.rrf_k + rank)
                sources[key].add(chunk.metadata.get("retrieval_source", "unknown"))

        ranked = sorted(scores, key=scores.get, reverse=True)
        candidates = []
        for key in ranked[: self.candidate_k]:
            chunk = merged[key]
            metadata = dict(chunk.metadata)
            metadata.update(
                {
                    "rrf_score": scores[key],
                    "rrf_sources": sorted(sources[key]),
                }
            )
            candidates.append(
                Result(page_content=chunk.page_content, metadata=metadata)
            )

        print(
            f"      [RRF] {len(candidates)} candidatos únicos | "
            f"listas: dense={len(dense_original) + len(dense_rewritten)}, "
            f"bm25={len(bm25_original) + len(bm25_rewritten)}"
        )
        return candidates

    def _get_reranker(self) -> CrossEncoder:
        device = "cuda" if torch.cuda.is_available() else "cpu"

        if self._reranker is None:
            print(f"      [CROSS-ENCODER] Cargando modelo '{self.reranker_model}'...")
            self._reranker = CrossEncoder(
                self.reranker_model,
                device=device,
                max_length=512,
            )
        return self._reranker

    def cross_encoder_rerank(self, question: str, chunks: list[Result]) -> list[Result]:
        if not chunks:
            return []

        t0 = time.time()
        reranker = self._get_reranker()
        pairs = [(question, chunk.page_content) for chunk in chunks]
        scores = reranker.predict(
            pairs,
            batch_size=self.reranker_batch_size,
            show_progress_bar=False,
        )

        ranked = sorted(
            zip(chunks, scores),
            key=lambda item: float(item[1]),
            reverse=True,
        )

        final = []
        for chunk, score in ranked:
            metadata = dict(chunk.metadata)
            metadata["cross_encoder_score"] = float(score)
            metadata["retrieval_source"] = "hybrid"
            final.append(Result(page_content=chunk.page_content, metadata=metadata))

        print(
            f"      [CROSS-ENCODER] {len(final)} candidatos reordenados en "
            f"{time.time()-t0:.2f}s"
        )
        return final

    async def fetch_context(
        self,
        question: str,
        tenant_id: str = "global",
        collections: list[str] | None = None,
    ):
        """
        Pipeline híbrido optimizado:

            Query
              │
              ├── Query original
              │      ├── Dense
              │      └── BM25
              │
              └── Query reescrita (solo si es necesaria)
                     ├── Dense
                     └── BM25
                              │
                              ▼
                             RRF
                              │
                              ▼
                        Cross-Encoder
                              │
                              ▼
                           final_k

        Se mantiene:
        - aislamiento multitenant
        - Dense Retrieval
        - BM25
        - RRF
        - Cross-Encoder
        - contrato de respuesta existente
        """

        print(
            "\n"
            "======================================================================\n"
            "[RAG - FETCH] Pipeline HÍBRIDO OPTIMIZADO\n"
            "Dense + BM25 + RRF + Cross-Encoder\n"
            "======================================================================"
        )

        t0 = time.time()

        # ================================================================
        # 1. NORMALIZACIÓN DE LA CONSULTA
        # ================================================================

        question = " ".join(question.strip().split())

        if not question:
            return {
                "chunks": [],
                "rewritten_query": question,
                "dense_original": [],
                "dense_rewritten": [],
                "bm25_original": [],
                "bm25_rewritten": [],
                "candidates": [],
                "retrieval": {
                    "original_query": question,
                    "rewritten_query": question,
                    "retrieved_chunks": 0,
                    "rewritten_chunks": 0,
                    "merged_chunks": 0,
                    "candidate_chunks": 0,
                    "final_chunks": 0,
                    "reranking": True,
                    "reranker": self.reranker_model,
                },
            }

        # ================================================================
        # 2. DECISIÓN DE REWRITING
        # ================================================================

        t_rewrite = time.time()

        rewrite_required = self.should_rewrite_query(question)

        if rewrite_required:
            rewritten = self.rewrite_query(question)

            # Evitamos resultados extraños del LLM.
            rewritten = " ".join(rewritten.strip().split())

            if not rewritten:
                rewritten = question

            print(f"      [REWRITE] ACTIVADO | " f"{time.time() - t_rewrite:.2f}s")
            print(f"      Original : '{question}'")
            print(f"      Rewritten: '{rewritten}'")

        else:
            # ------------------------------------------------------------
            # No necesitamos LLM.
            #
            # Muy importante:
            # no hacemos una segunda recuperación idéntica.
            # ------------------------------------------------------------

            rewritten = question

            print(
                f"      [REWRITE] OMITIDO | "
                f"consulta suficientemente directa | "
                f"{time.time() - t_rewrite:.2f}s"
            )

        # ================================================================
        # 3. RETRIEVAL
        # ================================================================

        t_retrieval = time.time()

        if rewritten == question:
            # ============================================================
            # FAST PATH
            #
            # No tiene sentido hacer:
            #
            # Dense(original)
            # Dense(rewritten)
            # BM25(original)
            # BM25(rewritten)
            #
            # porque las consultas son idénticas.
            #
            # Ejecutamos solamente:
            #
            # Dense + BM25
            #
            # en paralelo.
            # ============================================================

            print("      [RETRIEVAL] FAST PATH: " "Dense + BM25 en paralelo")

            dense_original, bm25_original = await asyncio.gather(
                self.retrieve(
                    question,
                    tenant_id=tenant_id,
                    collections=collections,
                ),
                self.retrieve_bm25(
                    question,
                    tenant_id=tenant_id,
                    collections=collections,
                ),
            )

            dense_rewritten = dense_original
            bm25_rewritten = bm25_original

        else:
            # ============================================================
            # PIPELINE COMPLETA
            #
            # Las cuatro búsquedas son independientes.
            # ============================================================

            print("      [RETRIEVAL] Pipeline completa: " "4 búsquedas en paralelo")

            (
                dense_original,
                dense_rewritten,
                bm25_original,
                bm25_rewritten,
            ) = await asyncio.gather(
                self.retrieve(
                    question,
                    tenant_id=tenant_id,
                    collections=collections,
                ),
                self.retrieve(
                    rewritten,
                    tenant_id=tenant_id,
                    collections=collections,
                ),
                self.retrieve_bm25(
                    question,
                    tenant_id=tenant_id,
                    collections=collections,
                ),
                self.retrieve_bm25(
                    rewritten,
                    tenant_id=tenant_id,
                    collections=collections,
                ),
            )

        print(
            f"      [RETRIEVAL] "
            f"{time.time() - t_retrieval:.2f}s | "
            f"Dense original={len(dense_original)} | "
            f"Dense rewritten={len(dense_rewritten)} | "
            f"BM25 original={len(bm25_original)} | "
            f"BM25 rewritten={len(bm25_rewritten)}"
        )

        # ================================================================
        # 4. RRF
        # ================================================================

        t_rrf = time.time()

        candidates = self.rrf_fusion(
            dense_original,
            dense_rewritten,
            bm25_original,
            bm25_rewritten,
        )

        print(
            f"      [RRF] "
            f"{len(candidates)} candidatos | "
            f"{time.time() - t_rrf:.2f}s"
        )

        # ================================================================
        # 5. CROSS-ENCODER
        # ================================================================

        t_rerank = time.time()

        # ------------------------------------------------------------
        # IMPORTANTE:
        #
        # cross_encoder_rerank() es síncrona y pesada.
        #
        # La ejecutamos en un thread para NO bloquear el event loop
        # de FastAPI.
        # ------------------------------------------------------------

        reranked = await asyncio.to_thread(
            self.cross_encoder_rerank,
            question,
            candidates,
        )

        print(
            f"      [CROSS-ENCODER] "
            f"{len(candidates)} candidatos reordenados en "
            f"{time.time() - t_rerank:.2f}s"
        )

        # ================================================================
        # 6. TOP-K FINAL
        # ================================================================

        final_chunks = reranked[: self.final_k]

        elapsed = time.time() - t0

        print(
            f"\n"
            f"   [RAG - FETCH] Final: {len(final_chunks)} chunks | "
            f"candidatos: {len(candidates)} | "
            f"{elapsed:.2f}s\n"
        )

        # ================================================================
        # 7. RESULTADO
        # ================================================================

        return {
            "chunks": final_chunks,
            "rewritten_query": rewritten,
            "dense_original": dense_original,
            "dense_rewritten": dense_rewritten,
            "bm25_original": bm25_original,
            "bm25_rewritten": bm25_rewritten,
            "candidates": candidates,
            "retrieval": {
                "original_query": question,
                "rewritten_query": rewritten,
                # --------------------------------------------------------
                # Compatibilidad ChatResponse
                # --------------------------------------------------------
                "retrieved_chunks": len(dense_original),
                "rewritten_chunks": len(dense_rewritten),
                "merged_chunks": len(candidates),
                # --------------------------------------------------------
                # Métricas del pipeline híbrido
                # --------------------------------------------------------
                "dense_original_chunks": len(dense_original),
                "dense_rewritten_chunks": len(dense_rewritten),
                "bm25_original_chunks": len(bm25_original),
                "bm25_rewritten_chunks": len(bm25_rewritten),
                "candidate_chunks": len(candidates),
                "final_chunks": len(final_chunks),
                "retrieval_k": self.retrieval_k,
                "bm25_k": self.bm25_k,
                "candidate_k": self.candidate_k,
                "final_k": self.final_k,
                "rrf_k": self.rrf_k,
                "reranking": True,
                "reranker": self.reranker_model,
                # --------------------------------------------------------
                # Información adicional de optimización
                # --------------------------------------------------------
                "query_rewriting": rewrite_required,
                "parallel_retrieval": True,
            },
        }

    async def fetch_context_simple(
        self, question, tenant_id="global", collections=None
    ):

        return await self.fetch_context(
            question,
            tenant_id,
            collections,
        )

    def build_prompt(self, question: str, history: list, chunks: list[Result]):
        context = "\n\n".join(
            f"Extrae de {c.metadata.get('source', 'fuente_desconocida')}:\n{c.page_content}"
            for c in chunks
        )
        return (
            [{"role": "system", "content": self.SYSTEM_PROMPT.format(context=context)}]
            + history
            + [{"role": "user", "content": question}]
        )

    async def simple_chat(self, question: str, history: list | None = None):
        history = history or []
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT.format(context="")}
        ]
        messages += history + [{"role": "user", "content": question}]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return {
            "answer": response.choices[0].message.content,
            "chunks": [],
            "retrieval": None,
        }

    async def answer(
        self,
        question: str,
        history: list | None = None,
        tenant_id: str = "global",
        collections: list[str] | None = None,
        model: str | None = None,
    ):
        print(f"\n{'='*70}")
        print("INICIANDO RAG PIPELINE HÍBRIDO")
        print(f"Pregunta: {question}")
        print(f"Tenant: {tenant_id} | Modelo: {model or self.model}")
        print(f"{'='*70}")

        t_total = time.time()
        history = history or []
        active_model = model or self.model

        retrieval = await self.fetch_context(
            question,
            tenant_id=tenant_id,
            collections=collections,
        )
        chunks = retrieval["chunks"]

        print(f"\nPregunta:\n{question}\n")
        print(f"Consulta reescrita:\n{retrieval['rewritten_query']}\n")
        print("Ranking final Cross-Encoder:")
        for i, chunk in enumerate(chunks, start=1):
            print(
                f"Chunk {i} | CE={chunk.metadata.get('cross_encoder_score', 0):.4f} | "
                f"RRF={chunk.metadata.get('rrf_score', 0):.6f} | "
                f"Fuente={chunk.metadata.get('source', 'fuente_desconocida')}"
            )

        messages = self.build_prompt(question, history, chunks)
        t_gen = time.time()
        response = self.client.chat.completions.create(
            model=active_model,
            messages=messages,
        )

        print(f"Generación completada en {time.time()-t_gen:.2f}s")
        print(f"RAG COMPLETADO EN {time.time()-t_total:.2f}s\n{'='*70}\n")

        return {
            "answer": response.choices[0].message.content,
            "chunks": chunks,
            "retrieval": retrieval["retrieval"],
        }

    # ------------------------------------------------------------------
    # Evaluación existente, conservada para no romper tu pipeline.
    # ------------------------------------------------------------------
    def calculate_mrr(self, keyword: str, retrieved_docs: list) -> float:
        keyword_lower = keyword.lower()
        for rank, doc in enumerate(retrieved_docs, start=1):
            if keyword_lower in doc.page_content.lower():
                return 1.0 / rank
        return 0.0

    def calculate_dcg(self, relevances: list[int], k: int) -> float:
        dcg = 0.0
        for i in range(min(k, len(relevances))):
            dcg += relevances[i] / math.log2(i + 2)
        return dcg

    def calculate_ndcg(self, keyword: str, retrieved_docs: list, k: int = 10) -> float:
        keyword_lower = keyword.lower()
        relevances = [
            1 if keyword_lower in doc.page_content.lower() else 0
            for doc in retrieved_docs[:k]
        ]
        dcg = self.calculate_dcg(relevances, k)
        ideal_relevances = sorted(relevances, reverse=True)
        idcg = self.calculate_dcg(ideal_relevances, k)
        return dcg / idcg if idcg > 0 else 0.0

    async def evaluate_retrieval(
        self, test, tenant_id: str, collections: list[str] | None = None, k: int = 10
    ) -> RetrievalEval:
        context_data = await self.fetch_context(
            test.question, tenant_id=tenant_id, collections=collections
        )
        retrieved_docs = context_data["chunks"]
        top_k_docs = retrieved_docs[:k]

        mrr_scores = [
            self.calculate_mrr(keyword, retrieved_docs) for keyword in test.keywords
        ]
        ndcg_scores = [
            self.calculate_ndcg(keyword, retrieved_docs, k) for keyword in test.keywords
        ]

        avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0
        avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0
        keywords_found = sum(1 for score in mrr_scores if score > 0)
        total_keywords = len(test.keywords)
        coverage = (keywords_found / total_keywords * 100) if total_keywords else 0.0

        relevant_docs_count = 0
        for doc in top_k_docs:
            doc_text = getattr(doc, "page_content", str(doc))
            if any(keyword.lower() in doc_text.lower() for keyword in test.keywords):
                relevant_docs_count += 1

        accuracy = (relevant_docs_count / len(top_k_docs) * 100) if top_k_docs else 0.0

        return RetrievalEval(
            mrr=avg_mrr,
            ndcg=avg_ndcg,
            keywords_found=keywords_found,
            total_keywords=total_keywords,
            keyword_coverage=coverage,
            accuracy=accuracy,
        )

    async def evaluate_answer(
        self, test, tenant_id: str
    ) -> tuple[AnswerEval, str, list]:
        generated_answer_result = await self.answer(
            test.question,
            history=[],
            tenant_id=tenant_id,
        )
        generated_answer = generated_answer_result["answer"]
        retrieved_docs = generated_answer_result["chunks"]

        prompt = f"""
        Pregunta:
        {test.question}

        Respuesta generada:
        {generated_answer}

        Respuesta de referencia:
        {test.reference_answer}

        Evalúa:
        1. Precisión (accuracy).
        2. Exhaustividad (completeness).
        3. Pertinencia (relevance).

        Devuelve JSON con feedback, accuracy, completeness y relevance.
        """
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un evaluador experto. Responde solo en JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format=AnswerEval,
        )
        eval_result = completion.choices[0].message.parsed
        return eval_result, generated_answer, retrieved_docs

    async def knowledge_graph(self):
        """Mantiene el método original; no constituye un knowledge graph real."""
        stmt = (
            select(Chunk, Embedding, Document)
            .join(Embedding, Embedding.chunk_id == Chunk.id)
            .join(Document, Document.id == Chunk.document_id)
        )

        async with AsyncSessionLocal() as session:
            result_proxy = await session.execute(stmt)
            rows = result_proxy.all()

        graph = []
        for chunk, embedding, document in rows:
            graph.append(
                {
                    "document_id": str(document.id),
                    "source": document.filename,
                    "headline": chunk.headline,
                    "summary": chunk.summary,
                    "content": chunk.content,
                    "embedding_dimension": (
                        len(embedding.vector) if embedding.vector else 0
                    ),
                }
            )
        return graph
