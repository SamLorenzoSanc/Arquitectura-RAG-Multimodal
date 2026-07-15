from pydantic import BaseModel, Field
from typing import List, Literal
from uuid import UUID

class TenantCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)

class AssignTenantRequest(BaseModel):
    user_id: str
    tenant_id: str
class TenantUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    active: bool | None = None