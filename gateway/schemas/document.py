from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
class DocumentBase(BaseModel):
    filename: str
    title: Optional[str] = None
    description: Optional[str] = None
    mime_type: str
    storage_path: str
    size: int
class DocumentCreate(DocumentBase):
    tenant_id: UUID
    knowledge_base_id: UUID

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class Document(DocumentBase):
    id: UUID
    tenant_id: UUID
    knowledge_base_id: UUID
    owner_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    title: str | None = None
    description: str | None = None
    mime_type: str
    size: int
    uploaded_at: datetime
    status: str


class UploadResponse(BaseModel):
    id: UUID
    message: str


class StatusResponse(BaseModel):
    document_id: UUID
    status: str
    chunks_generated: int
    started_at: datetime | None
    finished_at: datetime | None