from __future__ import annotations

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

from pydantic import BaseModel
from typing import Optional


class DepartmentCreateRequest(BaseModel):
    organization_id: str
    name: str
    description: Optional[str] = None


class DepartmentUpdateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class AddMemberPayload(BaseModel):
    email: str
    role_id: Optional[str] = None


# Compatibilidad legacy.
class DepartmentMemberRequest(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    role_id: Optional[str] = None



from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = None
    logo: str | None = None
    active: bool = True

class OrganizationCreateRequest(OrganizationBase):
    pass

class OrganizationUpdateRequest(BaseModel):
    name: str
    description: str | None = None

class OrganizationResponse(OrganizationBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OrganizationListResponse(BaseModel):
    items: list[OrganizationResponse]
    total: int