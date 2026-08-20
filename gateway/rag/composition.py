from dataclasses import dataclass
import os

from rag.adapters.outbound.bm25 import Bm25LexicalIndex
from rag.adapters.outbound.ollama import OllamaEmbeddingAdapter, OllamaLlmAdapter
from rag.adapters.outbound.pgvector import PgvectorChunkRepository
from rag.adapters.outbound.reranker import CrossEncoderReranker
from rag.application.answer import AnswerQuestion
from rag.application.evaluate import EvaluateAnswer, EvaluateRetrieval
from rag.application.ingest import IngestDocument
from rag.application.retrieve import HybridRetrieve


@dataclass
class RagContainer:
    llm: OllamaLlmAdapter
    embeddings: OllamaEmbeddingAdapter
    chunks: PgvectorChunkRepository
    lexical: Bm25LexicalIndex
    reranker: CrossEncoderReranker
    retrieve: HybridRetrieve
    answer: AnswerQuestion
    ingest: IngestDocument
    evaluate_retrieval: EvaluateRetrieval
    evaluate_answer: EvaluateAnswer


def build_rag_container(
    *,
    model: str = "llama3.2:latest",
    embedding_model: str | None = None,
    retrieval_k: int = 10,
    bm25_k: int = 10,
    rrf_k: int = 60,
    candidate_k: int = 15,
    final_k: int = 3,
    reranker_model: str = "BAAI/bge-reranker-v2-m3",
    reranker_batch_size: int = 16,
    bm25_index_dir: str | None = None,
) -> RagContainer:
    embedding_model = embedding_model or os.getenv(
        "RAG_EMBEDDING_MODEL", "nomic-embed-text"
    )
    llm = OllamaLlmAdapter()
    embeddings = OllamaEmbeddingAdapter(model=embedding_model)
    chunks = PgvectorChunkRepository(embeddings, embedding_model=embedding_model)
    lexical = Bm25LexicalIndex(index_dir=bm25_index_dir)
    reranker = CrossEncoderReranker(
        model_name=reranker_model, batch_size=reranker_batch_size
    )
    retrieve = HybridRetrieve(
        chunks,
        lexical,
        llm,
        reranker,
        retrieval_k=retrieval_k,
        bm25_k=bm25_k,
        rrf_k=rrf_k,
        candidate_k=candidate_k,
        final_k=final_k,
        chat_model=model,
        embedding_model=embedding_model,
        reranker_model=reranker_model,
    )
    return RagContainer(
        llm=llm,
        embeddings=embeddings,
        chunks=chunks,
        lexical=lexical,
        reranker=reranker,
        retrieve=retrieve,
        answer=AnswerQuestion(retrieve, llm, model),
        ingest=IngestDocument(lexical),
        evaluate_retrieval=EvaluateRetrieval(retrieve),
        evaluate_answer=EvaluateAnswer(llm, model),
    )
