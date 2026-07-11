from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class DocumentInfo(BaseModel):
    id: UUID
    filename: str
    document_type: str
    uploaded_at: datetime
    indexed: bool


class UploadResponse(BaseModel):
    id: UUID
    filename: str
    status: str


class DeleteResponse(BaseModel):
    deleted: bool
    document_id: UUID