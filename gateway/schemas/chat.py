from pydantic import BaseModel, Field
from typing import List, Literal
from uuid import UUID


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):

    question: str
    history: list[dict] = Field(default_factory=list)
    conversation_id: str | None = None
    retrieval_k: int = 20
    final_k: int = 10
    model: str = "ollama/llama3"
    temperature: float = 0
    use_query_rewrite: bool = True
    use_reranking: bool = True

class ContextChunk(BaseModel):
    page_content: str
    metadata: dict


class ChatResponse(BaseModel):
    answer: str
    context: list[ContextChunk]