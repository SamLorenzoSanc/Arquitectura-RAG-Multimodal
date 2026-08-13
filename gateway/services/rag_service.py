from __future__ import annotations

import hashlib
import math
import os
import pickle
import re
import time
import unicodedata
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from rank_bm25 import BM25Okapi
from sqlalchemy import cast, func, select
from pgvector.sqlalchemy import Vector
from tenacity import wait_exponential
import asyncio
from services.database import AsyncSessionLocal
from schemas.chat import Result
from models.chunk import Chunk
from models.document import Document
from models.embedding import Embedding
from schemas.evaluation import AnswerEvaluation
from services.evaluation_metrics import (
    abstention_score,
    citation_accuracy,
    numeric_match,
)

load_dotenv(override=True)
WAIT_POLICY = wait_exponential(multiplier=1, min=10, max=240)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")
HNSW_INDEX_DIMENSIONS = int(os.getenv("HNSW_INDEX_DIMENSIONS", "2000"))
DEFAULT_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "qwen3-embedding:latest")
DEFAULT_CHAT_MODEL = os.getenv("RAG_GENERATION_MODEL", "llama3.2:latest")

# Límites de generación: el cuello de botella típico está en Ollama, no en retrieval.
# 640 permite procedimiento + datos técnicos + recambios sin recortar la respuesta.
RAG_MAX_TOKENS = int(os.getenv("RAG_MAX_TOKENS", "640"))
RAG_TEMPERATURE = float(os.getenv("RAG_TEMPERATURE", "0"))
RAG_CHUNK_CHAR_LIMIT = int(os.getenv("RAG_CHUNK_CHAR_LIMIT", "600"))
RAG_KEEP_ALIVE = os.getenv("RAG_KEEP_ALIVE", "30m")
RAG_RELATED_QUESTIONS = max(1, int(os.getenv("RAG_RELATED_QUESTIONS", "5")))

# Expansión léxica agrícola (sin LLM): mejora BM25 en milisegundos.
_AGRO_SYNONYMS: dict[str, str] = {
    "riego": "riego irrigación gotero aspersión",
    "tomate": "tomate solanum lycopersicum",
    "plátano": "plátano banana musa",
    "platano": "plátano banana musa",
    "papaya": "papaya carica",
    "aguacate": "aguacate palta persea",
    "papa": "papa patata solanum tuberosum",
    "viña": "viña vid uva viticultura",
    "vina": "viña vid uva viticultura",
    "posei": "posei ayudas subvenciones canarias",
    "subvención": "subvención ayuda prima incentivo",
    "subvencion": "subvención ayuda prima incentivo",
    "plaga": "plaga insecto patogeno enfermedad fitosanitario",
    "fertilizante": "fertilizante abono nutriente npk",
    "suelo": "suelo edafologia materia organica",
    "sequía": "sequía deficit hidrico estres hidrico",
    "sequia": "sequía deficit hidrico estres hidrico",
    "gotero": "gotero goteros goteo filtro recambio taponamiento",
    "recambio": "recambio recambios pieza filtro junta fusible sonda gotero",
    "herramienta": "herramienta tijera podadora llave destornillador EPI",
    "cámara": "cámara camara frio reefer temperatura sonda",
    "camara": "cámara camara frio reefer temperatura sonda",
}
# Por defecto sin Cross-Encoder: el ranking final es el de RRF (mucho más rápido).
RAG_USE_RERANKER = os.getenv("RAG_USE_RERANKER", "false").lower() in {
    "1",
    "true",
    "yes",
}
RAG_USE_QUERY_REWRITE = os.getenv("RAG_USE_QUERY_REWRITE", "false").lower() in {
    "1",
    "true",
    "yes",
}

# Cache de retrieval para evitar ejecutar el pipeline dos veces
# (frontend llama /retrieve y luego /chat/ con la misma pregunta).
_RETRIEVAL_CACHE: OrderedDict[str, tuple[float, dict]] = OrderedDict()
_RETRIEVAL_CACHE_TTL = int(os.getenv("RETRIEVAL_CACHE_TTL", "120"))
_RETRIEVAL_CACHE_MAX_SIZE = int(os.getenv("RETRIEVAL_CACHE_MAX_SIZE", "256"))
_RETRIEVAL_CACHE_LOCK = Lock()
_RERANKERS: dict[str, object] = {}
_RERANKERS_LOCK = Lock()


def _retrieval_cache_key(
    tenant_id: str, question: str, collections: list[str] | None
) -> str:
    cols = ",".join(sorted(collections or []))
    raw = f"{tenant_id}|{question.strip()}|{cols}"
    return hashlib.sha256(raw.encode()).hexdigest()


class RetrievalEval(BaseModel):
    mrr: float = Field(description="Mean Reciprocal Rank")
    ndcg: float = Field(description="Normalized Discounted Cumulative Gain")
    keywords_found: int = Field(description="Número de keywords encontradas")
    total_keywords: int = Field(description="Número total de keywords")
    keyword_coverage: float = Field(description="Cobertura porcentual de keywords")
    accuracy: float = Field(description="Acierto globales de la búsqueda")


class DatasetEvaluationRequest(BaseModel):
    model_name: str = "llama3.2"
    embedding_model: str = "qwen3-embedding:latest"
    top_k: int = 5
    retrieval_k: int = 10
    bm25_k: int = 10
    rrf_k: int = 60
    candidate_k: int = 15
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_batch_size: int = 16


class DatasetEvaluationResponse(BaseModel):
    run_id: int
    model_name: str
    embedding_model: str
    dataset_size: int
    normal_questions: int
    different_info_questions: int
    out_of_knowledge_questions: int
    recall_1: float
    recall_k: float
    mrr: float
    false_positives: int
    failures: int
    duration_ms: float
    status: str
    parameters: dict


class EvaluationHistoryItem(BaseModel):
    id: int
    created_at: str
    model_name: str
    embedding_model: str
    dataset_size: int
    top_k: int
    recall_1: float
    recall_k: float
    mrr: float
    false_positives: int
    failures: int
    duration_ms: float
    status: str


class EvaluationResultItem(BaseModel):
    id: int
    dataset_id: int
    question: str
    expected_chunk_id: str | None
    retrieved_chunk_ids: list[str]
    retrieved_scores: list[float]
    expected_rank: int | None
    hit_at_1: bool
    hit_at_k: bool
    reciprocal_rank: float
    false_positive: bool
    failure: bool
    flag_different_info: bool
    flag_out_of_knowledge: bool
    retrieval_latency_ms: float | None


class RAGService:
    """RAG híbrido multitenant: Dense + BM25 + RRF + Cross-Encoder."""

    SYSTEM_PROMPT = """
    Eres AgroPS, el asistente de campo para agricultores de Canarias.
    Tu misión es resolver problemas reales de la explotación: riego, plagas,
    poda, cosecha, fertilización, maquinaria, cámara de frío y recambios.

    Responde SIEMPRE en español. Usa el perfil operativo del agricultor cuando exista.
    Usa la información del Contexto documental; si falta evidencia, dilo sin inventar
    y ofrece un procedimiento genérico seguro marcado como orientación.

    Estructura OBLIGATORIA de cada respuesta (usa exactamente estos títulos):
    1. Diagnóstico
       Qué ocurre y la causa más probable, en 2-4 frases.
    2. Procedimiento paso a paso
       Lista numerada de acciones concretas, en orden, que el agricultor pueda ejecutar.
    3. Información técnica
       Dosis, tiempos, temperaturas, caudales, presiones, carencias, umbrales o
       normativa que aparezcan en el Contexto. Si no hay cifras, indícalo.
    4. Herramientas y recambios
       Lista de herramientas, EPI, consumibles y piezas (goteros, filtros, juntas,
       fusibles, sondas, etc.). Si el documento no las nombra, sugiere lo habitual
       y márcalo como orientación.
    5. Precauciones
       Seguridad, plazos de seguridad y cuándo llamar a un técnico o a Sanidad Vegetal.

    No resumas documentos: prioriza la tarea a realizar.
    No añadas avisos de confidencialidad salvo que el documento los contenga.

    {farmer_context}

    Contexto documental:
    {context}
    """

    # Cross-Encoder multilingüe adecuado para un corpus en español.
    # Se descarga de Hugging Face la primera vez que se instancia.
    DEFAULT_RERANKER = "BAAI/bge-reranker-v2-m3"

    def __init__(
        self,
        model: str = DEFAULT_CHAT_MODEL,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
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
            base_url=OLLAMA_BASE_URL,
            api_key=OLLAMA_API_KEY,
        )

        # Por defecto se comparte el directorio con el servicio de ingesta.
        self.bm25_index_dir = Path(
            bm25_index_dir or Path(__file__).resolve().parent / "bm25_indexes"
        )
        self.bm25_index_dir.mkdir(parents=True, exist_ok=True)

        self._bm25_cache: dict[str, tuple[float, BM25Okapi, list[dict]]] = {}
        self._bm25_lock = Lock()
        self._reranker = None

    async def _run_in_thread(self, func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    @staticmethod
    def expand_agro_query(question: str) -> str:
        """Expande términos agrarios sin LLM (coste ~0 ms)."""
        lower = question.lower()
        extras: list[str] = []
        for term, expansion in _AGRO_SYNONYMS.items():
            if term in lower:
                extras.append(expansion)
        if not extras:
            return question
        return f"{question} {' '.join(extras)}"

    @staticmethod
    def _topic_from_chunk(chunk: Result) -> str | None:
        meta = chunk.metadata or {}
        for key in ("headline", "title", "source"):
            value = meta.get(key)
            if isinstance(value, str) and value.strip():
                topic = value.replace(".pdf", "").replace("_", " ").strip()
                if len(topic) >= 4:
                    return topic[:80]
        text = (chunk.page_content or "").replace("\n", " ").strip()
        if not text:
            return None
        first = re.split(r"[.?!\n]", text, maxsplit=1)[0].strip()
        words = [w for w in first.split() if len(w) > 2][:8]
        topic = " ".join(words).strip(" -:;,")
        return topic[:80] if len(topic) >= 4 else None

    def generate_related_questions(
        self,
        question: str,
        chunks: list[Result],
        max_questions: int | None = None,
    ) -> list[str]:
        """Preguntas relacionadas agrícolas a partir del retrieval (sin LLM)."""
        limit = max_questions or RAG_RELATED_QUESTIONS
        templates = [
            "¿Cuáles son los pasos para resolver un problema de {topic}?",
            "¿Qué herramientas y recambios se necesitan para {topic}?",
            "¿Qué datos técnicos (dosis, tiempos, temperaturas) aplican a {topic}?",
            "¿Cómo diagnosticar y corregir un fallo de {topic}?",
            "¿Qué precauciones de seguridad hay al trabajar {topic}?",
        ]
        seen: set[str] = set()
        out: list[str] = []
        q_norm = " ".join(question.lower().split())
        seen.add(q_norm)

        topics: list[str] = []
        for chunk in chunks:
            topic = self._topic_from_chunk(chunk)
            if not topic:
                continue
            key = topic.lower()
            if key in seen:
                continue
            seen.add(key)
            topics.append(topic)

        for i, topic in enumerate(topics):
            tmpl = templates[i % len(templates)]
            candidate = tmpl.format(topic=topic)
            key = candidate.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(candidate)
            if len(out) >= limit:
                return out

        # Fallbacks útiles si hay poco contexto recuperado.
        fallbacks = [
            "Tengo goteros taponados: ¿cómo los limpio paso a paso y qué recambios llevo?",
            "¿Cómo podo el plátano y qué herramientas necesito?",
            "La cámara no mantiene el frío: ¿qué reviso y qué piezas pueden fallar?",
            "Hay manchas en hoja: ¿cómo identifico la plaga y qué tratamiento aplico?",
            "¿Cuál es el procedimiento de carga a reefer y qué controles de frío hago?",
        ]
        for fb in fallbacks:
            if fb.lower() in seen:
                continue
            out.append(fb)
            if len(out) >= limit:
                break
        return out

    async def _create_embeddings(self, question: str):
        return await asyncio.to_thread(
            self.client.embeddings.create,
            model=self.embedding_model,
            input=[question],
        )

    async def _create_completion(self, model: str, messages: list[dict]):
        # OpenAI-compatible: max_tokens limita la respuesta.
        # Extra body keep_alive evita recargar el modelo en cada request (Ollama).
        return await asyncio.to_thread(
            self.client.chat.completions.create,
            model=model,
            messages=messages,
            temperature=RAG_TEMPERATURE,
            max_tokens=RAG_MAX_TOKENS,
            extra_body={"keep_alive": RAG_KEEP_ALIVE},
        )

    async def _create_parse_completion(
        self, model: str, messages: list[dict], response_format
    ):
        return await asyncio.to_thread(
            self.client.beta.chat.completions.parse,
            model=model,
            messages=messages,
            response_format=response_format,
        )

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
        await asyncio.to_thread(self._dump_bm25_payload, tmp_path, payload)
        tmp_path.replace(path)

        corpus = [self._tokenize(d["text"]) for d in documents]
        if not corpus:
            return None
        return BM25Okapi(corpus), documents, path.stat().st_mtime

    def _dump_bm25_payload(self, tmp_path: Path, payload: dict):
        with tmp_path.open("wb") as fh:
            pickle.dump(payload, fh, protocol=pickle.HIGHEST_PROTOCOL)

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
            loaded = await asyncio.to_thread(self._load_bm25_file, tenant_id)
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

    @staticmethod
    def invalidate_retrieval_cache(tenant_id: str | None = None) -> int:
        with _RETRIEVAL_CACHE_LOCK:
            if tenant_id is None:
                count = len(_RETRIEVAL_CACHE)
                _RETRIEVAL_CACHE.clear()
                return count
            prefix = f"{tenant_id}|"
            keys = [
                key
                for key in _RETRIEVAL_CACHE
                if _RETRIEVAL_CACHE[key][1].get("_cache_scope", "").startswith(prefix)
            ]
            for key in keys:
                _RETRIEVAL_CACHE.pop(key, None)
            return len(keys)

    async def rewrite_query(self, question: str, history: list | None = None) -> str:
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
        response = await self._create_completion(
            self.model,
            [{"role": "system", "content": prompt}],
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
        """Dense retrieval local mediante pgvector con filtro multitenant."""
        t0 = time.time()
        raw_embedding = (await self._create_embeddings(question)).data[0].embedding
        t_emb = time.time() - t0
        index_dimensions = min(HNSW_INDEX_DIMENSIONS, len(raw_embedding))
        approximate_distance = func.subvector(
            Embedding.vector, 1, index_dimensions
        ).cast(Vector(index_dimensions)).cosine_distance(
            raw_embedding[:index_dimensions]
        )

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

        # El índice HNSW usa un subvector (pgvector limita la dimensión indexable);
        # la distancia exacta completa se conserva en el resultado.
        stmt = stmt.order_by(approximate_distance).limit(self.retrieval_k)

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
                        "embedding_latency_ms": t_emb * 1000,
                        "dense_latency_ms": (time.time() - t0) * 1000,
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
        bm25_latency_ms = (time.time() - t0) * 1000
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
                        "bm25_latency_ms": bm25_latency_ms,
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

    def _get_reranker(self):
        # Import lazy: no cargar torch/sentence-transformers si el rerank está off.
        import torch
        from sentence_transformers import CrossEncoder

        device = "cuda" if torch.cuda.is_available() else "cpu"
        cache_key = f"{self.reranker_model}:{device}"
        if self._reranker is None:
            with _RERANKERS_LOCK:
                if cache_key not in _RERANKERS:
                    print(f"      [CROSS-ENCODER] Cargando modelo '{self.reranker_model}' en {device}...")
                    _RERANKERS[cache_key] = CrossEncoder(
                        self.reranker_model, device=device, max_length=512
                    )
                self._reranker = _RERANKERS[cache_key]
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
        evaluation_mode: bool = False,
        use_reranking: bool | None = None,
        use_query_rewrite: bool | None = None,
    ):
        """
        Pipeline: Dense + BM25 + RRF → final_k.
        Cross-Encoder y query-rewrite están opcionales (desactivados por defecto).
        """

        question = " ".join(question.strip().split())
        do_rerank = RAG_USE_RERANKER if use_reranking is None else bool(use_reranking)
        allow_rewrite = (
            RAG_USE_QUERY_REWRITE
            if use_query_rewrite is None
            else bool(use_query_rewrite)
        )

        cache_key = _retrieval_cache_key(
            tenant_id,
            f"{question}|rr={int(do_rerank)}|rw={int(allow_rewrite)}",
            collections,
        )
        now = time.time()
        with _RETRIEVAL_CACHE_LOCK:
            cached = None if evaluation_mode else _RETRIEVAL_CACHE.get(cache_key)
            if cached and (now - cached[0]) < _RETRIEVAL_CACHE_TTL:
                _RETRIEVAL_CACHE.move_to_end(cache_key)
                print(
                    "[RAG - FETCH] CACHE HIT — reutilizando retrieval previo "
                    f"(edad: {now - cached[0]:.1f}s)"
                )
                return cached[1]

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
                    "reranking": False,
                    "reranker": None,
                },
            }

        # ================================================================
        # 2. DECISIÓN DE REWRITING
        # ================================================================

        t_rewrite = time.time()
        rewrite_required = allow_rewrite and self.should_rewrite_query(question)

        if rewrite_required:
            rewritten = await self.rewrite_query(question)
            rewritten = " ".join(rewritten.strip().split()) or question
            print(f"      [REWRITE] ACTIVADO | {time.time() - t_rewrite:.2f}s")
            print(f"      Original : '{question}'")
            print(f"      Rewritten: '{rewritten}'")
        else:
            rewritten = question
            print(
                f"      [REWRITE] OMITIDO | "
                f"{'desactivado' if not allow_rewrite else 'consulta directa'} | "
                f"{time.time() - t_rewrite:.2f}s"
            )
        rewrite_latency_ms = (time.time() - t_rewrite) * 1000

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

            bm25_query = self.expand_agro_query(question)
            dense_original, bm25_original = await asyncio.gather(
                self.retrieve(
                    question,
                    tenant_id=tenant_id,
                    collections=collections,
                ),
                self.retrieve_bm25(
                    bm25_query,
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
                    self.expand_agro_query(question),
                    tenant_id=tenant_id,
                    collections=collections,
                ),
                self.retrieve_bm25(
                    self.expand_agro_query(rewritten),
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
        retrieval_latency_ms = (time.time() - t_retrieval) * 1000

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
        rrf_latency_ms = (time.time() - t_rrf) * 1000

        # ================================================================
        # 5. CROSS-ENCODER (opcional; desactivado por defecto)
        # ================================================================

        t_rerank = time.time()
        if do_rerank:
            ranked = await asyncio.to_thread(
                self.cross_encoder_rerank,
                question,
                candidates,
            )
            print(
                f"      [CROSS-ENCODER] {len(candidates)} candidatos en "
                f"{time.time() - t_rerank:.2f}s"
            )
        else:
            ranked = candidates
            print("      [CROSS-ENCODER] OMITIDO — ranking RRF directo")
        rerank_latency_ms = (time.time() - t_rerank) * 1000

        # ================================================================
        # 6. TOP-K FINAL
        # ================================================================

        final_chunks = ranked[: self.final_k]

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

        result = {
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
                "reranking": do_rerank,
                "reranker": self.reranker_model if do_rerank else None,
                # --------------------------------------------------------
                # Información adicional de optimización
                # --------------------------------------------------------
                "query_rewriting": rewrite_required,
                "parallel_retrieval": True,
                "timings_ms": {
                    "rewrite": rewrite_latency_ms,
                    "retrieval_parallel": retrieval_latency_ms,
                    "rrf": rrf_latency_ms,
                    "reranking": rerank_latency_ms,
                    "total_retrieval": elapsed * 1000,
                    "embedding": max(
                        (
                            chunk.metadata.get("embedding_latency_ms", 0.0)
                            for chunk in dense_original
                        ),
                        default=0.0,
                    ),
                    "dense": max(
                        (
                            chunk.metadata.get("dense_latency_ms", 0.0)
                            for chunk in dense_original
                        ),
                        default=0.0,
                    ),
                    "bm25": max(
                        (
                            chunk.metadata.get("bm25_latency_ms", 0.0)
                            for chunk in bm25_original
                        ),
                        default=0.0,
                    ),
                },
            },
        }

        if not evaluation_mode:
            result["_cache_scope"] = f"{tenant_id}|{','.join(sorted(collections or []))}"
            with _RETRIEVAL_CACHE_LOCK:
                _RETRIEVAL_CACHE[cache_key] = (time.time(), result)
                _RETRIEVAL_CACHE.move_to_end(cache_key)
                while len(_RETRIEVAL_CACHE) > _RETRIEVAL_CACHE_MAX_SIZE:
                    _RETRIEVAL_CACHE.popitem(last=False)

        return result

    async def fetch_context_simple(
        self, question, tenant_id="global", collections=None
    ):

        return await self.fetch_context(
            question,
            tenant_id,
            collections,
        )

    def build_prompt(
        self,
        question: str,
        history: list,
        chunks: list[Result],
        farmer_context: str | None = None,
    ):
        # Truncar chunks evita prompts enormes: más tokens de contexto = más latencia en Ollama.
        parts = []
        for c in chunks:
            body = c.page_content or ""
            if len(body) > RAG_CHUNK_CHAR_LIMIT:
                body = body[:RAG_CHUNK_CHAR_LIMIT].rstrip() + "…"
            source = c.metadata.get("source", "fuente_desconocida")
            parts.append(f"Extrae de {source}:\n{body}")
        context = "\n\n".join(parts)
        # Historial acotado: solo últimos turnos para no hinchar el prompt.
        trimmed_history = (history or [])[-6:]
        farmer_block = (farmer_context or "").strip() or "Sin perfil operativo de parcela."
        return (
            [
                {
                    "role": "system",
                    "content": self.SYSTEM_PROMPT.format(
                        context=context,
                        farmer_context=farmer_block,
                    ),
                }
            ]
            + trimmed_history
            + [{"role": "user", "content": question}]
        )

    async def simple_chat(self, question: str, history: list | None = None):
        history = history or []
        messages = [
            {
                "role": "system",
                "content": self.SYSTEM_PROMPT.format(
                    context="",
                    farmer_context="Sin perfil operativo de parcela.",
                ),
            }
        ]
        messages += history + [{"role": "user", "content": question}]
        response = await self._create_completion(self.model, messages)
        return {
            "answer": response.choices[0].message.content,
            "chunks": [],
            "retrieval": None,
            "related_questions": self.generate_related_questions(question, []),
        }

    async def answer(
        self,
        question: str,
        history: list | None = None,
        tenant_id: str = "global",
        collections: list[str] | None = None,
        model: str | None = None,
        use_reranking: bool | None = None,
        use_query_rewrite: bool | None = None,
        farmer_context: str | None = None,
        farmer_profile: dict | None = None,
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
            use_reranking=use_reranking,
            use_query_rewrite=use_query_rewrite,
        )
        chunks = retrieval["chunks"]

        print(f"\nPregunta:\n{question}\n")
        print(f"Consulta reescrita:\n{retrieval['rewritten_query']}\n")
        print("Ranking final (RRF" + ("+CE" if retrieval.get("retrieval", {}).get("reranking") else "") + "):")
        for i, chunk in enumerate(chunks, start=1):
            print(
                f"Chunk {i} | CE={chunk.metadata.get('cross_encoder_score', 0):.4f} | "
                f"RRF={chunk.metadata.get('rrf_score', 0):.6f} | "
                f"Fuente={chunk.metadata.get('source', 'fuente_desconocida')}"
            )

        messages = self.build_prompt(
            question, history, chunks, farmer_context=farmer_context
        )
        t_gen = time.time()
        response = await self._create_completion(active_model, messages)
        generation_latency_ms = (time.time() - t_gen) * 1000

        related_questions = self.generate_related_questions(question, chunks)

        print(f"Generación completada en {time.time()-t_gen:.2f}s")
        print(f"RAG COMPLETADO EN {time.time()-t_total:.2f}s\n{'='*70}\n")

        # Include both the compact retrieval summary and the full
        # retrieval pipeline details for frontend debugging/visualization.
        retrieval["retrieval"].setdefault("timings_ms", {})[
            "generation"
        ] = generation_latency_ms
        retrieval["retrieval"]["timings_ms"]["total_rag"] = (
            time.time() - t_total
        ) * 1000
        retrieval["related_questions"] = related_questions
        if farmer_profile:
            retrieval["farmer_profile"] = farmer_profile
        return {
            "answer": response.choices[0].message.content,
            "chunks": chunks,
            "retrieval": retrieval.get("retrieval", {}),
            "retrieval_details": retrieval,
            "related_questions": related_questions,
            "farmer_profile": farmer_profile,
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
        self,
        question: str,
        generated_answer: str,
        retrieved_docs: list,
        reference_answer: str | None = None,
        out_of_knowledge: bool = False,
    ) -> tuple[AnswerEvaluation, str, list]:
        context = "\n\n".join(
            getattr(doc, "page_content", str(doc)) for doc in retrieved_docs
        )
        sources = [
            str(getattr(doc, "metadata", {}).get("source", ""))
            for doc in retrieved_docs
        ]
        prompt = f"""
        Pregunta: {question}
        Respuesta de referencia: {reference_answer or "No disponible"}
        Respuesta Generada: {generated_answer}
        Contexto recuperado: {context or "Sin contexto"}
        Fuera de conocimiento: {out_of_knowledge}
        Puntúa accuracy, completeness, relevance, faithfulness y groundedness de 1 a 5.
        citation_accuracy, numeric_match y abstention deben estar entre 0 y 1.
        La referencia mide corrección; el contexto mide fidelidad. No premies afirmaciones
        correctas que no estén respaldadas por el contexto cuando se evalúe groundedness.
        """
        completion = await self._create_parse_completion(
            self.model,
            [
                {
                    "role": "system",
                    "content": "Eres un evaluador experto. Responde solo en JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            AnswerEvaluation,
        )
        eval_result = completion.choices[0].message.parsed
        if eval_result is None:
            raise RuntimeError("El juez no devolvió una evaluación estructurada")
        # Las métricas deterministas prevalecen sobre estimaciones del juez.
        eval_result.numeric_match = numeric_match(reference_answer, generated_answer)
        eval_result.citation_accuracy = citation_accuracy(generated_answer, sources)
        eval_result.abstention = abstention_score(generated_answer, out_of_knowledge)
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
