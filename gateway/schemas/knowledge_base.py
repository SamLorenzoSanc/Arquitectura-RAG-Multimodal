from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

PROJECT_USE_CASES = (
    "Agentic Application",
    "Chatbot",
    "Q/A",
    "Consulta normativa",
    "Sanidad vegetal",
    "Otros",
)


class KnowledgeBaseBase(BaseModel):
    name: str
    description: Optional[str] = None
    use_case: Optional[str] = None

class KnowledgeBaseCreate(BaseModel):
    """
    Datos necesarios para crear una Knowledge Base / proyecto.
    """

    name: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Nombre del proyecto",
    )

    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Descripción del caso de uso",
    )

    use_case: str | None = Field(
        default="Q/A",
        max_length=80,
        description="Caso de uso del proyecto",
    )

class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    use_case: Optional[str] = None

class KnowledgeBase(KnowledgeBaseBase):
    id: UUID
    tenant_id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True 