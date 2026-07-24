from pathlib import Path
from chromadb import PersistentClient
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from schemas.chat import RankOrder, Result
from tenacity import retry, wait_exponential
from traceback import print_exc
from typing import Any
import math
import json
import os
import urllib.request
load_dotenv(override=True)
WAIT_POLICY = wait_exponential(multiplier=1, min=10, max=240)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "chroma"))
class RetrievalEval(BaseModel):
    mrr: float = Field(description="Mean Reciprocal Rank")
    ndcg: float = Field(description="Normalized Discounted Cumulative Gain")
    keywords_found: int = Field(description="Número de keywords encontradas")
    total_keywords: int = Field(description="Número total de keywords")
    keyword_coverage: float = Field(description="Cobertura porcentual de keywords")
class AnswerEval(BaseModel):
    feedback: str = Field(description="Comentarios sobre la respuesta")
    accuracy: float = Field(description="Precisión factual de 1 a 5")
    completeness: float = Field(description="Exhaustividad de 1 a 5")
    relevance: float = Field(description="Pertinencia de 1 a 5")
class RAGService:
    SYSTEM_PROMPT = """
    Eres un asistente experto y amable que representa a la empresa AgroTech.
    Si el usuario pregunta por información contenida en el contexto, RESPÓNDELA con precisión técnica y profesional.
    No te niegues a responder información técnica o corporativa si esta se encuentra dentro del Contexto facilitado.
    No añadas avisos de confidencialidad a menos que el documento mismo los contenga explícitamente.
    REGLA CRÍTICA DE IDIOMA: Debe responder SIEMPRE en español.
    Contexto:
    {context}
    """
    def __init__(
        self,
        model: str = "llama3",
        embedding_model: str = "qwen3-embedding:latest",
        db_path: str | None = None,
        collection_name: str = "docs",
        retrieval_k: int = 20,
        final_k: int = 10,
    ):
        print(f"[DEBUG] Inicializando RAGService en ruta: {BASE_DIR}")
        self.chroma = PersistentClient(path=BASE_DIR)
        all_cols = self.chroma.list_collections()
        print(f"[DEBUG] Colecciones encontradas: {[c.name for c in all_cols]}")
        self.collection = self.chroma.get_or_create_collection("documents")
        print(f"[DEBUG] Conectado a colección por defecto: {self.collection.name} con {self.collection.count()} documentos")
        self.model = model
        self.embedding_model = embedding_model
        self.retrieval_k = retrieval_k
        self.final_k = final_k
        self.wait = wait_exponential(multiplier=1, min=10, max=240)
        self.client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    def get_embeddings(self):
        return self.embedding_model
    def rewrite_query(self, question: str, history: list | None = None) -> str:
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
        return response.choices[0].message.content.strip()
    def retrieve(self, question: str, tenant_id: str = "global", collections: list[str] | None = None) -> list[Result]:
        embedding = self.client.embeddings.create(
            model=self.embedding_model,
            input=[question],
        ).data[0].embedding
        target_cols = []
        if collections:
            for col_name in collections:
                try:
                    col = self.chroma.get_collection(col_name)
                    target_cols.append(col)
                except Exception as e:
                    print(f"[WARN] No se pudo obtener la colección '{col_name}': {e}")
        # Si no se pasaron colecciones o no existen, usa la colección por defecto
        if not target_cols:
            target_cols = [self.collection]
        chunks = []
        # Consultar cada colección objetivo y consolidar
        for col in target_cols:
            where_clause = None
            # Si usamos la colección global "documents", aplicamos el filtro por tenant
            if col.name == "documents":
                where_clause = {
                    "$or": [
                        {"tenant_id": tenant_id},
                        {"tenant_id": "global"},
                    ]
                }
            results = col.query(
                query_embeddings=[embedding],
                n_results=self.retrieval_k,
                where=where_clause,
            )
            docs = results.get("documents")
            metas = results.get("metadatas")
            if docs and metas and len(docs[0]) > 0:
                for doc, meta in zip(docs[0], metas[0]):
                    chunks.append(Result(page_content=doc, metadata=meta or {}))
        # Desduplicar fragmentos preservando el orden
        unique_chunks = []
        seen = set()
        for chunk in chunks:
            if chunk.page_content not in seen:
                seen.add(chunk.page_content)
                unique_chunks.append(chunk)
        return unique_chunks
    def merge_chunks(self, chunks1: list[Result], chunks2: list[Result]) -> list[Result]:
        merged = chunks1.copy()
        existing = {chunk.page_content for chunk in chunks1}
        for chunk in chunks2:
            if chunk.page_content not in existing:
                merged.append(chunk)
        return merged
    def rerank(self, question: str, chunks: list[Result]) -> list[Result]:
        if not chunks:
            return []
        system_prompt = """
            Eres un sistema de reordenación de documentos.
            REGLA CRÍTICA DE IDIOMA: Debe responder SIEMPRE en español.
            Se te proporciona una pregunta y una lista de fragmentos de texto relevantes.
            Debes clasificar los fragmentos por relevancia.
            Responde únicamente con la lista de identificadores de los fragmentos clasificados.
        """
        user_prompt = f"Pregunta:\n{question}\n\nFragmentos:\n"
        for index, chunk in enumerate(chunks):
            user_prompt += f"# CHUNK ID: {index + 1}\n{chunk.page_content}\n\n"
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=RankOrder,
        )
        reply = response.choices[0].message.content
        order = RankOrder.model_validate_json(reply).order
        return [chunks[i - 1] for i in order if 0 < i <= len(chunks)]
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
    def fetch_context_simple(self, question: str, tenant_id: str = "global", collections: list[str] | None = None):
        rewritten = self.rewrite_query(question)
        original = self.retrieve(question, tenant_id=tenant_id, collections=collections)
        rewritten_chunks = self.retrieve(rewritten, tenant_id=tenant_id, collections=collections)
        merged = self.merge_chunks(original, rewritten_chunks)
        final_chunks = merged[: self.final_k]
        return {
            "rewritten_query": rewritten,
            "original": original,
            "rewritten_chunks": rewritten_chunks,
            "merged": merged,
            "chunks": final_chunks,
        }
    def fetch_context(self, question: str, tenant_id: str = "global", collections: list[str] | None = None):
        rewritten = self.rewrite_query(question)
        original = self.retrieve(question, tenant_id=tenant_id, collections=collections)
        rewritten_chunks = self.retrieve(rewritten, tenant_id=tenant_id, collections=collections)
        merged = self.merge_chunks(original, rewritten_chunks)
        reranked = self.rerank(question, merged)
        final_chunks = reranked[: self.final_k]
        return {
            "chunks": final_chunks,
            "retrieval": {
                "original_query": question,
                "rewritten_query": rewritten,
                "retrieved_chunks": len(original),
                "rewritten_chunks": len(rewritten_chunks),
                "merged_chunks": len(merged),
                "final_chunks": len(final_chunks),
                "retrieval_k": self.retrieval_k,
                "final_k": self.final_k,
                "reranking": True,
            },
        }
    def simple_chat(self, question: str, history: list | None = None):
        history = history or []
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT.format(context="")}]
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
    def answer(
        self,
        question: str,
        history: list | None = None,
        tenant_id: str = "global",
        collections: list[str] | None = None,
        model: str | None = None,  # <--- ASEGÚRATE DE AÑADIR ESTE PARÁMETRO AQUÍ
    ):
        history = history or []
        
        # Si se pasa un modelo desde el endpoint, lo usamos; si no, caemos en el por defecto de la clase
        active_model = model or self.model 

        retrieval = self.fetch_context_simple(question, tenant_id=tenant_id, collections=collections)
        chunks = retrieval["chunks"]
        messages = self.build_prompt(question, history, chunks)
        
        # Usamos 'active_model' en lugar de 'self.model' fijo
        response = self.client.chat.completions.create(
            model=active_model,  
            messages=messages,
        )
        return {
            "answer": response.choices[0].message.content,
            "chunks": chunks,
            "retrieval": {
                "original_query": question,
                "rewritten_query": retrieval["rewritten_query"],
                "retrieved_chunks": len(retrieval["original"]),
                "rewritten_chunks": len(retrieval["rewritten_chunks"]),
                "merged_chunks": len(retrieval["merged"]),
                "final_chunks": len(chunks),
                "retrieval_k": self.retrieval_k,
                "final_k": self.final_k,
                "reranking": False,
            },
        }
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
        relevances = [1 if keyword_lower in doc.page_content.lower() else 0 for doc in retrieved_docs[:k]]
        dcg = self.calculate_dcg(relevances, k)
        ideal_relevances = sorted(relevances, reverse=True)
        idcg = self.calculate_dcg(ideal_relevances, k)
        return dcg / idcg if idcg > 0 else 0.0
    def evaluate_retrieval(self, test, tenant_id: str, collections: list[str] | None = None, k: int = 10) -> RetrievalEval:
        retrieved_docs = self.fetch_context_simple(test.question, tenant_id=tenant_id, collections=collections)["chunks"]
        mrr_scores = [self.calculate_mrr(keyword, retrieved_docs) for keyword in test.keywords]
        ndcg_scores = [self.calculate_ndcg(keyword, retrieved_docs, k) for keyword in test.keywords]
        avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0
        avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0
        keywords_found = sum(1 for score in mrr_scores if score > 0)
        total_keywords = len(test.keywords)
        coverage = (keywords_found / total_keywords * 100) if total_keywords else 0.0
        return RetrievalEval(
            mrr=avg_mrr,
            ndcg=avg_ndcg,
            keywords_found=keywords_found,
            total_keywords=total_keywords,
            keyword_coverage=coverage,
        )
    def evaluate_answer(self, test, tenant_id: str) -> tuple[AnswerEval, str, list]:
        """Genera la respuesta vía RAG y la evalúa contra la referencia usando el LLM."""
        
        # 1. Obtener la respuesta del RAG
        generated_answer_result = self.answer(test.question, history=[], tenant_id=tenant_id)
        generated_answer = generated_answer_result["answer"]
        retrieved_docs = generated_answer_result["chunks"]
        # 2. Construir el prompt de evaluación
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
        # 3. Llamar a OpenAI con Structured Outputs (.parse)
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": "Eres un evaluador experto. Responde solo en JSON."},
                {"role": "user", "content": prompt},
            ],
            response_format=AnswerEval,
        )
        eval_result = completion.choices[0].message.parsed
        return eval_result, generated_answer, retrieved_docs
        return eval_result, generated_answer, retrieved_docs
    def evaluate_all_retrieval(self, tests, tenant_id: str, collections: list[str] | None = None):
        results = []
        for test in tests:
            result = self.evaluate_retrieval(test, tenant_id=tenant_id, collections=collections)
            results.append({
                "question": test.question,
                "category": test.category,
                "mrr": result.mrr,
                "ndcg": result.ndcg,
                "keywords_found": result.keywords_found,
                "total_keywords": result.total_keywords,
                "keyword_coverage": result.keyword_coverage,
            })
        return results
    def evaluate_all_answers(self, tests, tenant_id: str, collections: list[str] | None = None):
        results = []
        for test in tests:
            result, generated_answer, _ = self.evaluate_answer(test, tenant_id=tenant_id, collections=collections)
            results.append({
                "question": test.question,
                "category": test.category,
                "feedback": result.feedback,
                "accuracy": result.accuracy,
                "completeness": result.completeness,
                "relevance": result.relevance,
                "generated_answer": generated_answer,
            })
        return results
    def knowledge_graph(self):
        return self.collection.get(include=["embeddings", "documents", "metadatas"])