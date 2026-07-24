from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from uuid import UUID


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class RAGMetadata(BaseModel):
    original_query: str
    rewritten_query: str | None

    retrieval_k: int
    final_k: int

    retrieved_chunks: int
    returned_chunks: int

    embedding_model: str
    llm_model: str

    reranking: bool
    query_rewrite: bool

    elapsed_ms: float
class ChatRequest(BaseModel):
    question: str
    history: list[dict] = Field(default_factory=list)
    conversation_id: str | None = None
    knowledge_base_id: Optional[str] = None
    retrieval_k: int = 20
    final_k: int = 10
    model: str | None = None
    temperature: float = 0
    use_query_rewrite: bool = True
    use_reranking: bool = True

class ContextChunk(BaseModel):
    type: str
    page_content: str
    metadata: dict

class RetrievalInfo(BaseModel):
    original_query: str
    rewritten_query: str
    retrieved_chunks: int
    rewritten_chunks: int
    merged_chunks: int
    final_chunks: int
    retrieval_k: int
    final_k: int
    reranking: bool
class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    context: list[ContextChunk]
    retrieval: RetrievalInfo
class Result(BaseModel):
    page_content: str
    metadata: dict


class RankOrder(BaseModel):
    order: list[int] = Field(
        description="Orden de relevancia de los fragmentos"
    )

