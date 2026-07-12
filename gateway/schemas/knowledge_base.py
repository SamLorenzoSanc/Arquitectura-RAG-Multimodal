from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class KnowledgeBaseBase(BaseModel):
    name: str
    description: Optional[str] = None
    chroma_collection: str

class KnowledgeBaseCreate(KnowledgeBaseBase):
    tenant_id: UUID

class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    chroma_collection: Optional[str] = None

class KnowledgeBase(KnowledgeBaseBase):
    id: UUID
    tenant_id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True