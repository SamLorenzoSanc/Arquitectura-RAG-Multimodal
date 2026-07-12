from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Literal

JobStatus = Literal["PENDING", "PROCESSING", "COMPLETED", "FAILED"]

class ProcessingJobBase(BaseModel):
    status: JobStatus = "PENDING"
    error_message: Optional[str] = None

class ProcessingJobCreate(ProcessingJobBase):
    document_id: UUID

class ProcessingJobUpdate(BaseModel):
    status: JobStatus
    error_message: Optional[str] = None

class ProcessingJob(ProcessingJobBase):
    id: UUID
    document_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True