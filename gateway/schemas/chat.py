from pydantic import BaseModel, Field
from typing import Any, Literal, Optional


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
    architecture: str | None = None
    agent_tools: list[str] | None = None


class ChatRequest(BaseModel):
    question: str
    history: list[dict] = Field(default_factory=list)
    conversation_id: str | None = None
    knowledge_base_id: Optional[str] = None
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    retrieval_k: int = 10
    final_k: int = 3
    model: str | None = None
    temperature: float = 0
    # Desactivados por defecto: menos latencia (respuesta ~1 llamada LLM).
    use_query_rewrite: bool = False
    use_reranking: bool = False
    use_rag: bool = True
    # Comparación controlada Hybrid vs Agentic
    rag_mode: Literal["hybrid", "agentic", "compare"] = "hybrid"
    island: Optional[str] = "La_Palma"
    crop: Optional[str] = "platano_canarias"
    # Parcela estructurada del agricultor (prioridad sobre crop/island)
    crop_id: Optional[str] = None


class ModeComparisonSide(BaseModel):
    mode: str
    architecture: str | None = None
    answer: str
    context: list[ContextChunk] = Field(default_factory=list)
    retrieval: RetrievalInfo | None = None
    retrieval_details: dict | None = None
    agent_trace: list[dict] | None = None
    related_questions: list[str] = Field(default_factory=list)
    latency_ms: float | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    context: list[ContextChunk]
    retrieval: RetrievalInfo | None = None
    retrieval_details: dict | None = None
    related_questions: list[str] = Field(default_factory=list)
    rag_mode: str | None = None
    architecture: str | None = None
    agent_trace: list[dict] | None = None
    comparison: dict[str, Any] | None = None
    farmer_profile: dict[str, Any] | None = None


class Result(BaseModel):
    page_content: str
    metadata: dict


class RankOrder(BaseModel):
    order: list[int] = Field(description="Orden de relevancia de los fragmentos")
