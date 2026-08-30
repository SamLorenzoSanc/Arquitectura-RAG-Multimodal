from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    

from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    name: str
    email: EmailStr
    active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    active: Optional[bool] = None
    password: Optional[str] = None

class User(UserBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True 

from pydantic import BaseModel, Field
from typing import List, Literal
from uuid import UUID

class TenantCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: str | None = None

class AssignTenantRequest(BaseModel):
    user_id: str
    tenant_id: str
class TenantUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    active: bool | None = None

from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from uuid import UUID

class Chunk(BaseModel):
    id: UUID
    document_id: UUID
    index: int

    headline: str
    summary: str
    original_text: str

    metadata: dict = {}

class Chunks(BaseModel):

    chunks: list[Chunk]


from pydantic import BaseModel


class EmbeddedChunk(BaseModel):

    chunk: Chunk

    embedding: list[float]

from pydantic import BaseModel


class ServiceHealth(BaseModel):
    service: str
    status: str


class HealthResponse(BaseModel):
    gateway: ServiceHealth
    rag_service: ServiceHealth
    ingestion_service: ServiceHealth
    chromadb: ServiceHealth
    ollama: ServiceHealth

from pydantic import BaseModel


class MetricsResponse(BaseModel):
    requests: int
    average_latency: float
    retrieval_time: float
    generation_time: float
    reranking_time: float

from pydantic import BaseModel


class ModelInfo(BaseModel):
    name: str
    provider: str
    context_window: int
    embedding_model: str


class ModelSelection(BaseModel):
    model_name: str


class ModelSelectionResponse(BaseModel):
    active_model: str

from pydantic import BaseModel


class SpeechWord(BaseModel):
    word: str
    start: float
    end: float
    probability: float


class SpeechSegment(BaseModel):
    start: float
    end: float
    text: str
    words: list[SpeechWord]


class SpeechResponse(BaseModel):
    text: str
    language: str
    duration: float
    segments: list[SpeechSegment]


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