from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from uuid import UUID


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[dict] = Field(default_factory=list)
    conversation_id: str | None = None
    knowledge_base_id: Optional[str] = None
    retrieval_k: int = 20
    final_k: int = 10
    model: str = "ollama/llama3"
    temperature: float = 0
    use_query_rewrite: bool = True
    use_reranking: bool = True

class ContextChunk(BaseModel):
    type: str
    page_content: str
    metadata: dict


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    context: list[ContextChunk]

class Result(BaseModel):
    page_content: str
    metadata: dict


class RankOrder(BaseModel):
    order: list[int] = Field(
        description="Orden de relevancia de los fragmentos"
    )
