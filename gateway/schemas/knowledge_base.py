from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

class KnowledgeBaseBase(BaseModel):
    name: str
    description: Optional[str] = None

class KnowledgeBaseCreate(BaseModel):
    """
    Datos necesarios para crear una Knowledge Base.
    """

    name: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Nombre de la base de conocimiento",
    )

    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Descripción opcional de la base de conocimiento",
    )
class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class KnowledgeBase(KnowledgeBaseBase):
    id: UUID
    tenant_id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True
        