from __future__ import annotations

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
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    logo: str | None = None
    active: bool | None = None

class OrganizationResponse(OrganizationBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OrganizationListResponse(BaseModel):
    items: list[OrganizationResponse]
    total: int